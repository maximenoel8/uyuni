# Copyright (c) 2024-2026 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/step_definitions/rke2_steps.rb.

Covers Kubernetes / RKE2 steps: cluster readiness, deployment wait,
external CA replacement and restoration, TFTP sanity checks.
"""

import time

from pytest_bdd import given, when, then, parsers

from support.remote_nodes_env import get_target
from support.commonlib import repeat_until_timeout
from support.env import DEFAULT_TIMEOUT


# ---------------------------------------------------------------------------
# First-time setup job
# ---------------------------------------------------------------------------

@given("The first-time setup job is successful")
def step_first_time_setup_job_successful():
    cmd = (
        "kubectl get jobs -n uyuni -l app.kubernetes.io/component=server-setup "
        "-o jsonpath='{.items[0].status.succeeded}'"
    )
    status, code = get_target("server").run_local(cmd)
    assert code == 0, "Failed to get server setup job status"
    assert int(status.strip() or 0) >= 1, "Server setup job did not succeed"


@then('the setup marker file should exist on "server"')
def step_setup_marker_file_exists():
    server_pod = _get_pod_name("server", "server")
    cmd = (
        f"kubectl exec -n uyuni {server_pod} -- "
        "test -f /root/.MANAGER_SETUP_COMPLETE && echo 'EXISTS'"
    )
    status, code = get_target("server").run_local(cmd)
    assert code == 0, "Failed to check server setup marker file"
    assert "EXISTS" in status, "Server setup marker file does not exist"


# ---------------------------------------------------------------------------
# Kubernetes cluster readiness
# ---------------------------------------------------------------------------

@given(parsers.re(r'The Kubernetes cluster is ready on "(?P<target>.*)"'))
def step_kubernetes_cluster_ready(target: str):
    _out, code = get_target(target).run_local("kubectl get nodes && kubectl get namespace uyuni")
    assert code == 0, f"Kubernetes cluster is not ready or uyuni namespace is missing on {target}"


# Alias for "And" prefix
@when(parsers.re(
    r'(?:the|I wait until the) "(?P<name>.*)" deployment on "(?P<target>.*)" '
    r'(?:becomes|should become) ready within (?P<mins>.*) minutes'
))
@given(parsers.re(
    r'(?:the|I wait until the) "(?P<name>.*)" deployment on "(?P<target>.*)" '
    r'(?:becomes|should become) ready within (?P<mins>.*) minutes'
))
def step_deployment_ready_within_when(name: str, target: str, mins: str):
    _wait_for_deployment(target, name, int(mins))


# ---------------------------------------------------------------------------
# External CA setup and teardown
# ---------------------------------------------------------------------------

@given("I back up the CA certificates on the server and proxy")
def step_backup_ca_certificates(context_store):
    backup_dir = "/root/ca-backup"
    ca_dir = "/root/test-external-ca"
    ca_cn = "External Test CA"

    context_store["backup_dir"] = backup_dir
    context_store["external_ca_dir"] = ca_dir
    context_store["external_ca_cn"] = ca_cn

    server = get_target("server")
    server.run_local(f"mkdir -p {backup_dir}")

    _out, code = server.run_local(
        f"kubectl get secret uyuni-ca -n cert-manager -o yaml "
        f"--show-managed-fields=false > {backup_dir}/uyuni-ca-secret.yaml"
    )
    assert code == 0, "Failed to backup uyuni-ca secret"

    _out, code = server.run_local(
        f"kubectl get certificate uyuni-ca -n cert-manager -o yaml "
        f"--show-managed-fields=false > {backup_dir}/uyuni-ca-cert.yaml"
    )
    assert code == 0, "Failed to backup uyuni-ca Certificate CR"

    try:
        proxy = get_target("proxy")
        proxy.run_local(f"mkdir -p {backup_dir}")
        proxy.run_local(
            f"kubectl get configmap uyuni-ca -n uyuni -o yaml "
            f"> {backup_dir}/uyuni-ca-configmap.yaml",
            check_errors=False
        )
    except Exception:
        print("Proxy configmap backup skipped (proxy not available yet)")


@when("I restore the original CA certificates on the server and proxy")
def step_restore_ca_certificates(context_store):
    backup_dir = context_store.get("backup_dir", "/root/ca-backup")
    ca_dir = context_store.get("external_ca_dir", "/root/test-external-ca")
    server = get_target("server")

    server.run_local("kubectl delete certificate uyuni-ca -n cert-manager --ignore-not-found")
    server.run_local("kubectl delete secret uyuni-ca -n cert-manager --ignore-not-found")
    server.run_local(f"kubectl apply -f {backup_dir}/uyuni-ca-secret.yaml")
    server.run_local(f"kubectl apply -f {backup_dir}/uyuni-ca-cert.yaml")

    server.run_local("kubectl delete secret uyuni-cert db-cert proxy-cert -n uyuni --ignore-not-found")
    for cert in ["uyuni-cert", "db-cert"]:
        server.run_local(
            f"kubectl get certificate {cert} -n uyuni -o yaml "
            f"--show-managed-fields=false > /tmp/{cert}-cr.yaml"
        )
        server.run_local(f"kubectl delete certificate {cert} -n uyuni --ignore-not-found")
        server.run_local(f"kubectl apply -f /tmp/{cert}-cr.yaml")
    server.run_local("kubectl delete certificate proxy-cert -n uyuni --ignore-not-found")

    def _cert_exists():
        _out, code = server.run_local(
            "kubectl get secret uyuni-cert -n uyuni", check_errors=False
        )
        if code == 0:
            return True
        time.sleep(5)
        return None

    repeat_until_timeout(_cert_exists, timeout=300,
                         message="uyuni-cert was not re-issued during restore")

    server.run_local(f"rm -rf {backup_dir} {ca_dir}")

    try:
        proxy = get_target("proxy")
        proxy.run_local(
            f"test -f {backup_dir}/uyuni-ca-configmap.yaml && "
            f"kubectl apply -f {backup_dir}/uyuni-ca-configmap.yaml --force",
            check_errors=False
        )
        proxy.run_local("kubectl delete secret proxy-cert -n uyuni --ignore-not-found",
                        check_errors=False)
        proxy.run_local(f"rm -rf {backup_dir}", check_errors=False)
    except Exception:
        print("Proxy restore skipped (proxy not available)")


# ---------------------------------------------------------------------------
# External CA replacement
# ---------------------------------------------------------------------------

@when(parsers.re(r'I generate an external CA on "(?P<target>.*)"'))
def step_generate_external_ca(target: str, context_store):
    ca_dir = context_store.get("external_ca_dir", "/root/test-external-ca")
    ca_cn = context_store.get("external_ca_cn", "External Test CA")
    get_target(target).run_local(f"mkdir -p {ca_dir}")
    _out, code = get_target(target).run_local(
        f"openssl ecparam -genkey -name prime256v1 -noout -out {ca_dir}/ca.key && "
        f"openssl req -new -x509 -key {ca_dir}/ca.key -out {ca_dir}/ca.crt "
        f"-days 3650 -subj '/C=DE/ST=Bayern/L=Nurnberg/O={ca_cn}/OU=Testing/CN=External CA'"
    )
    assert code == 0, "Failed to generate external CA"


@when(parsers.re(r'I replace the uyuni-ca secret with the external CA on "(?P<target>.*)"'))
def step_replace_uyuni_ca_secret(target: str, context_store):
    ca_dir = context_store.get("external_ca_dir", "/root/test-external-ca")
    node = get_target(target)
    node.run_local("kubectl delete certificate uyuni-ca -n cert-manager --ignore-not-found")
    node.run_local("kubectl delete secret uyuni-ca -n cert-manager --ignore-not-found")
    _out, code = node.run_local(
        f"kubectl create secret tls uyuni-ca -n cert-manager "
        f"--cert={ca_dir}/ca.crt --key={ca_dir}/ca.key"
    )
    assert code == 0, "Failed to replace uyuni-ca secret"


@when(parsers.re(r'I delete the leaf certificate secrets on "(?P<target>.*)"'))
def step_delete_leaf_certificate_secrets(target: str):
    _out, code = get_target(target).run_local(
        "kubectl delete secret uyuni-cert db-cert -n uyuni --ignore-not-found"
    )
    assert code == 0, "Failed to delete leaf certificate secrets"


@then(parsers.re(
    r'the "(?P<secret>.*)" secret on "(?P<target>.*)" should be re-issued within (?P<mins>\d+) minutes'
))
def step_secret_re_issued_within(secret: str, target: str, mins: str):
    def _exists():
        _out, code = get_target(target).run_local(
            f"kubectl get secret {secret} -n uyuni", check_errors=False
        )
        if code == 0:
            return True
        time.sleep(5)
        return None

    repeat_until_timeout(_exists, timeout=int(mins) * 60,
                         message=f"Secret {secret} was not re-issued")


@then(parsers.re(
    r'the "(?P<secret>.*)" certificate on "(?P<target>.*)" should be signed by the external CA'
))
def step_certificate_signed_by_external_ca(secret: str, target: str, context_store):
    ca_cn = context_store.get("external_ca_cn", "External Test CA")
    issuer, code = get_target(target).run_local(
        f"kubectl get secret {secret} -n uyuni "
        f"-o jsonpath='{{.data.tls\\.crt}}' | base64 -d | openssl x509 -noout -issuer"
    )
    assert code == 0, f"Failed to read issuer from {secret}"
    assert ca_cn in issuer, f"{secret} not signed by external CA. Issuer: {issuer}"


@when("I re-generate the proxy certificate on the server using the external CA")
def step_regenerate_proxy_certificate():
    proxy_fqdn = get_target("proxy").full_hostname
    server = get_target("server")

    server.run_local("kubectl delete certificate proxy-cert -n uyuni --ignore-not-found")
    server.run_local("kubectl delete secret proxy-cert -n uyuni --ignore-not-found")

    certificate_yaml = _render_certificate_yaml(
        name="proxy-cert",
        secret_name="proxy-cert",
        fqdn=proxy_fqdn,
        namespace="uyuni",
        issuer_name="uyuni-issuer",
        issuer_kind="ClusterIssuer",
        issuer_group="cert-manager.io",
        is_ca=False,
    )
    _out, code = server.run_local(
        f"cat <<'CERT_EOF' | kubectl apply -f -\n{certificate_yaml}\nCERT_EOF"
    )
    assert code == 0, "Failed to create proxy-cert Certificate resource"

    def _secret_created():
        _out, code = server.run_local(
            "kubectl get secret proxy-cert -n uyuni", check_errors=False
        )
        if code == 0:
            return True
        time.sleep(5)
        return None

    repeat_until_timeout(_secret_created, timeout=600,
                         message="proxy-cert secret was not created by cert-manager")


@when(parsers.re(r'I transfer the proxy certificate from the server to "(?P<target>.*)"'))
def step_transfer_proxy_certificate(target: str):
    from support.file_management import file_inject, generate_temp_file
    import yaml

    out, code = get_target("server").run_local(
        "kubectl get secret proxy-cert -n uyuni -o yaml --show-managed-fields=false"
    )
    assert code == 0, "Failed to extract proxy-cert secret from server"

    secret = yaml.safe_load(out)
    for key in ["uid", "resourceVersion", "creationTimestamp", "annotations"]:
        secret.get("metadata", {}).pop(key, None)
    clean_yaml = yaml.dump(secret)

    secret_file = "/tmp/proxy-cert-secret.yaml"
    temp_path = generate_temp_file("proxy-cert-secret", clean_yaml)
    success = file_inject(get_target(target), temp_path, secret_file)
    import os
    os.unlink(temp_path)
    assert success, "Failed to inject proxy-cert secret into proxy"

    _out, code = get_target(target).run_local(f"kubectl apply -f {secret_file}")
    assert code == 0, "Failed to apply proxy-cert secret on proxy cluster"


@when(parsers.re(r'I update the uyuni-ca configmap on "(?P<target>.*)" with the external CA'))
def step_update_uyuni_ca_configmap(target: str, context_store):
    from support.file_management import file_extract, file_inject
    ca_dir = context_store.get("external_ca_dir", "/root/test-external-ca")

    success = file_extract(get_target("server"), f"{ca_dir}/ca.crt", "/tmp/external-ca.crt")
    assert success, "Failed to extract external CA cert from server"

    success = file_inject(get_target(target), "/tmp/external-ca.crt", "/tmp/external-ca.crt")
    assert success, "Failed to inject external CA cert into proxy"

    _out, code = get_target(target).run_local(
        "kubectl delete configmap uyuni-ca -n uyuni --ignore-not-found && "
        "kubectl create configmap uyuni-ca -n uyuni --from-file=ca.crt=/tmp/external-ca.crt"
    )
    assert code == 0, "Failed to update uyuni-ca configmap on proxy"


# ---------------------------------------------------------------------------
# TFTP container sanity check
# ---------------------------------------------------------------------------

@then(parsers.re(
    r'the "(?P<svc>.*)" service on "(?P<target>.*)" should have at least one active endpoint'
))
def step_service_has_active_endpoint(svc: str, target: str):
    out, code = get_target(target).run_local(
        f"kubectl get endpoints {svc} -n uyuni "
        f"-o jsonpath='{{.subsets[0].addresses[0].ip}}'"
    )
    assert code == 0 and out.strip(), \
        f"Service '{svc}' has no active endpoints on '{target}'"


@given(parsers.re(r'I create a sanity-check file in the TFTP boot root on "(?P<target>.*)"'))
def step_create_tftp_sanity_file(target: str, context_store):
    server_pod = _get_pod_name(target, "server")
    tftp_probe_filename = "uyuni-tftp-sanity-probe.txt"
    tftp_probe_content = "uyuni-tftp-sanity-ok"
    context_store["tftp_probe_filename"] = tftp_probe_filename
    context_store["tftp_probe_content"] = tftp_probe_content
    get_target(target).run_local(
        f"kubectl exec -n uyuni {server_pod} -- "
        f"sh -c 'echo {tftp_probe_content} > /srv/tftpboot/{tftp_probe_filename}'"
    )


@when(parsers.re(r'I download the sanity-check file via TFTP from "(?P<target>.*)"'))
def step_download_tftp_sanity_file(target: str, context_store):
    node_port = _get_tftp_node_port(target)
    filename = context_store.get("tftp_probe_filename", "uyuni-tftp-sanity-probe.txt")
    local = f"/tmp/{filename}"
    context_store["tftp_probe_local_path"] = local
    get_target(target).run_local(
        f"curl --silent --show-error tftp://localhost:{node_port}/{filename} --output {local}"
    )


@then(parsers.re(
    r'the downloaded TFTP content should match the expected sanity-check content on "(?P<target>.*)"'
))
def step_downloaded_tftp_content_matches(target: str, context_store):
    local = context_store.get("tftp_probe_local_path", "/tmp/uyuni-tftp-sanity-probe.txt")
    expected = context_store.get("tftp_probe_content", "uyuni-tftp-sanity-ok")
    out, _code = get_target(target).run_local(f"cat {local}", check_errors=False)
    assert out.strip() == expected, \
        f"Content mismatch — expected: '{expected}', got: '{out.strip()}'"


@when(parsers.re(r'I remove the sanity-check file from the TFTP boot root on "(?P<target>.*)"'))
def step_remove_tftp_sanity_file(target: str, context_store):
    server_pod = _get_pod_name(target, "server")
    filename = context_store.get("tftp_probe_filename", "uyuni-tftp-sanity-probe.txt")
    local = context_store.get("tftp_probe_local_path", f"/tmp/{filename}")
    get_target(target).run_local(
        f"kubectl exec -n uyuni {server_pod} -- rm -f /srv/tftpboot/{filename}"
    )
    get_target(target).run_local(f"rm -f {local}", check_errors=False)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _wait_for_deployment(target: str, name: str, mins: int):
    """Wait for a Kubernetes deployment to become ready within N minutes."""
    timeout = mins * 60

    def _ready():
        _out, code = get_target(target).run_local(
            f"kubectl rollout status deployment/{name} -n uyuni --timeout=10s",
            check_errors=False
        )
        if code == 0:
            return True
        time.sleep(10)
        return None

    repeat_until_timeout(_ready, timeout=timeout,
                         message=f"Deployment {name} on {target} did not become ready")


def _get_pod_name(target: str, component: str) -> str:
    """Get the pod name for a given component in the uyuni namespace."""
    out, code = get_target(target).run_local(
        f"kubectl get pods -n uyuni -l app.kubernetes.io/component={component} "
        "-o jsonpath='{.items[0].metadata.name}'"
    )
    assert code == 0, f"Failed to get pod name for component {component}"
    return out.strip()


def _get_tftp_node_port(target: str) -> str:
    """Get the NodePort for the TFTP service."""
    out, code = get_target(target).run_local(
        "kubectl get service uyuni-proxy-tftpd -n uyuni "
        "-o jsonpath='{.spec.ports[0].nodePort}'"
    )
    assert code == 0, "Failed to get TFTP NodePort"
    return out.strip()


def _render_certificate_yaml(
    name: str,
    secret_name: str,
    fqdn: str,
    namespace: str,
    issuer_name: str,
    issuer_kind: str,
    issuer_group: str,
    is_ca: bool,
) -> str:
    """Render a cert-manager Certificate YAML resource."""
    is_ca_str = "true" if is_ca else "false"
    return f"""apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: {name}
  namespace: {namespace}
spec:
  secretName: {secret_name}
  isCA: {is_ca_str}
  dnsNames:
    - {fqdn}
  issuerRef:
    name: {issuer_name}
    kind: {issuer_kind}
    group: {issuer_group}
"""
