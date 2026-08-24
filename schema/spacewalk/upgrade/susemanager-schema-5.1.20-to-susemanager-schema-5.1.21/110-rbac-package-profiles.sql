--
-- Copyright (c) 2026 SUSE LLC
--
-- This software is licensed to you under the GNU General Public License,
-- version 2 (GPLv2). There is NO WARRANTY for this software, express or
-- implied, including the implied warranties of MERCHANTABILITY or FITNESS
-- FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
-- along with this software; if not, see
-- http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
--

-- Add namespace descriptions
UPDATE access.namespace SET description = 'View/compare package profiles'
    WHERE namespace = 'systems.profiles' AND access_mode = 'R';

UPDATE access.namespace SET description = 'Create/edit package profiles'
    WHERE namespace = 'systems.profiles' AND access_mode = 'W';

-- Insert missing profile endpoints
INSERT INTO access.endpoint (class_method, endpoint, http_method, scope, auth_required)
    SELECT '', '/systems/details/packages/profiles/CompareProfiles.do', 'POST', 'W', True
    WHERE NOT EXISTS (SELECT 1 FROM access.endpoint WHERE endpoint = '/systems/details/packages/profiles/CompareProfiles.do' AND http_method = 'POST');

INSERT INTO access.endpoint (class_method, endpoint, http_method, scope, auth_required)
    SELECT '', '/systems/details/packages/profiles/CompareSystems.do', 'GET', 'W', True
    WHERE NOT EXISTS (SELECT 1 FROM access.endpoint WHERE endpoint = '/systems/details/packages/profiles/CompareSystems.do' AND http_method = 'GET');

INSERT INTO access.endpoint (class_method, endpoint, http_method, scope, auth_required)
    SELECT '', '/systems/details/packages/profiles/CompareSystems.do', 'POST', 'W', True
    WHERE NOT EXISTS (SELECT 1 FROM access.endpoint WHERE endpoint = '/systems/details/packages/profiles/CompareSystems.do' AND http_method = 'POST');

-- Add profile endpoints to 'systems.profiles' namespace before removing legacy mappings.
INSERT INTO access.endpointNamespace (namespace_id, endpoint_id)
    SELECT ns.id, ep.id
    FROM access.namespace ns
    CROSS JOIN access.endpoint ep
    WHERE ns.namespace = 'systems.profiles' AND ns.access_mode = 'R'
    AND ep.endpoint IN (
        '/systems/details/packages/profiles/ShowProfiles.do',
        '/systems/details/packages/profiles/CompareProfiles.do',
        '/systems/details/packages/profiles/CompareSystems.do')
    AND ep.http_method IN ('GET', 'POST')
    AND ep.scope = 'W'
    ON CONFLICT DO NOTHING;

INSERT INTO access.endpointNamespace (namespace_id, endpoint_id)
    SELECT ns.id, ep.id
    FROM access.namespace ns
    CROSS JOIN access.endpoint ep
    WHERE ns.namespace = 'systems.profiles' AND ns.access_mode = 'W'
    AND ep.endpoint IN (
        '/systems/details/packages/profiles/Create.do',
        '/systems/details/packages/profiles/DeleteProfile.do')
    AND ep.http_method IN ('GET', 'POST')
    AND ep.scope = 'W'
    ON CONFLICT DO NOTHING;

-- Remove the replaced package-profile mappings.
DELETE FROM access.endpointNamespace old_mapping
USING access.namespace old_namespace, access.endpoint endpoint
WHERE old_mapping.namespace_id = old_namespace.id
    AND old_mapping.endpoint_id = endpoint.id
    AND old_namespace.namespace = 'systems.software.packages'
    AND old_namespace.access_mode = 'R'
    AND endpoint.endpoint IN (
        '/systems/details/packages/profiles/ShowProfiles.do',
        '/systems/details/packages/profiles/CompareProfiles.do',
        '/systems/details/packages/profiles/CompareSystems.do')
    AND endpoint.http_method IN ('GET', 'POST')
    AND endpoint.scope = 'W';

DELETE FROM access.endpointNamespace old_mapping
USING access.namespace old_namespace, access.endpoint endpoint
WHERE old_mapping.namespace_id = old_namespace.id
    AND old_mapping.endpoint_id = endpoint.id
    AND old_namespace.namespace = 'systems.software.packages'
    AND old_namespace.access_mode = 'W'
    AND endpoint.endpoint IN (
        '/systems/details/packages/profiles/Create.do',
        '/systems/details/packages/profiles/DeleteProfile.do')
    AND endpoint.http_method IN ('GET', 'POST')
    AND endpoint.scope = 'W';
