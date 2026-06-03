# Copyright (c) 2024 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/support/code_coverage.rb.

Provides CodeCoverage: runs JaCoCo CLI on the server, downloads the XML
report, parses covered source files, and pushes results into Redis.
"""

import os
import xml.etree.ElementTree as ET

from support.keyvalue_store import KeyValueStore
from support.remote_nodes_env import get_target

_JACOCO_CLI = "java -jar /tmp/jacococli.jar"
_DUMP_PATH_TPL = "/var/cache/jacoco-{feature_name}.exec"
_XML_PUB_TPL = "/srv/www/htdocs/pub/jacoco-{feature_name}.xml"
_HTML_PUB_TPL = "/srv/www/htdocs/pub/jacoco-{feature_name}"
_LOCAL_XML_TPL = "/tmp/jacoco-{feature_name}.xml"
_JAR_CLASSFILES = "--classfiles /srv/tomcat/webapps/rhn/WEB-INF/lib/rhn.jar"
_JAVA_SOURCEFILES = "--sourcefiles /tmp/uyuni-master/java/core/src/main/java"


class CodeCoverage:
    """Code Coverage handler for JaCoCo reports on the Java server."""

    def __init__(self):
        self._store = KeyValueStore(
            os.getenv("REDIS_HOST"),
            os.getenv("REDIS_PORT"),
            os.getenv("REDIS_USERNAME"),
            os.getenv("REDIS_PASSWORD"),
        )

    def jacoco_dump(self, feature_name: str, *,
                    html: bool = False, xml: bool = True, source: bool = False):
        """
        Generate a JaCoCo report on the server and download the XML locally.

        Mirrors Ruby's jacoco_dump: runs a `dump` step first (to capture
        live execution data), then a `report` step.

        :param feature_name: name used to label the report files
        :param html: whether to generate an HTML report (default: False)
        :param xml:  whether to generate an XML report  (default: True)
        :param source: whether to include Java source files (default: False)
        """
        server = get_target("server")
        dump_path = _DUMP_PATH_TPL.format(feature_name=feature_name)
        xml_pub = _XML_PUB_TPL.format(feature_name=feature_name)
        html_pub = _HTML_PUB_TPL.format(feature_name=feature_name)

        # Step 1: dump live execution data from the running JVM
        server.run(
            f"{_JACOCO_CLI} dump --address localhost "
            f"--destfile {dump_path} --port 6300 --reset",
            verbose=True,
        )

        # Step 2: build report from the dump
        report_parts = [
            f"{_JACOCO_CLI} report {dump_path}",
            _JAR_CLASSFILES,
        ]
        if xml:
            report_parts.append(f"--xml {xml_pub}")
        if html:
            report_parts.append(f"--html {html_pub}")
        if source:
            report_parts.append(_JAVA_SOURCEFILES)
        server.run(" ".join(report_parts), verbose=True)

        # Step 3: download the XML locally for parsing
        if xml:
            local_path = _LOCAL_XML_TPL.format(feature_name=feature_name)
            server.extract(xml_pub, local_path)

    def push_feature_coverage(self, feature_name: str):
        """
        Parse a local JaCoCo XML report and push covered source files to Redis.

        Coverage is determined by the CLASS counter: a source file is
        considered covered if its CLASS counter has at least one covered class.
        The local XML file is deleted after parsing (even on error).

        :param feature_name: name used to locate /tmp/jacoco-<feature_name>.xml
        """
        print(f"Pushing coverage for {feature_name} into Redis")
        local_path = _LOCAL_XML_TPL.format(feature_name=feature_name)
        if not os.path.exists(local_path):
            return
        try:
            tree = ET.parse(local_path)
            root = tree.getroot()
            for package in root.findall(".//package"):
                pkg_name = package.get("name", "")
                for source_file in package.findall("sourcefile"):
                    sf_name = source_file.get("name", "")
                    # Mirror Ruby: check the CLASS counter specifically
                    counter_class = source_file.find("counter[@type='CLASS']")
                    if counter_class is None:
                        continue
                    covered = int(counter_class.get("covered", "0"))
                    if covered <= 0:
                        continue
                    key = f"{pkg_name}/{sf_name}"
                    self._store.add(key, feature_name)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Warning: Could not parse JaCoCo XML for {feature_name}: {e}")
        finally:
            try:
                os.remove(local_path)
            except OSError:
                pass
