# Copyright (c) 2022-2025 SUSE LLC.
# Licensed under the terms of the MIT license.

# Image namespace


class NamespaceImage:
    def __init__(self, api_test):
        self._api = api_test
        self.profile = NamespaceImageProfile(api_test)
        self.store = NamespaceImageStore(api_test)

    def delete(self, imageid):
        """Deletes an image based on its ID."""
        return self._api.call("image.delete", imageid)

    def get_details(self, imageid):
        """Gets an image's details based on its ID."""
        return self._api.call("image.getDetails", imageid)

    def schedule_image_build(self, profile_label, version_build, build_hostid, date):
        """Schedules an image build for a given profile, version, build host, and date."""
        return self._api.call(
            "image.scheduleImageBuild",
            profile_label,
            version_build,
            build_hostid,
            date,
        )

    def list_images(self):
        """Returns a list of images."""
        return self._api.call("image.listImages")


class NamespaceImageProfile:
    def __init__(self, api_test):
        self._api = api_test

    def create(self, label, type, store_label, path, actkey):
        """Creates a new image profile."""
        return self._api.call(
            "image.profile.create", label, type, store_label, path, actkey
        )

    def delete(self, label):
        """Deletes a profile from the system."""
        return self._api.call("image.profile.delete", label)

    def set_custom_values(self, label, values):
        """Sets custom values for an image profile."""
        return self._api.call("image.profile.setCustomValues", label, values)

    def delete_custom_values(self, label, keys):
        """Deletes custom values from an image profile."""
        return self._api.call("image.profile.deleteCustomValues", label, keys)

    def get_custom_values(self, label):
        """Returns the custom values for a given label."""
        return self._api.call("image.profile.getCustomValues", label)

    def list_image_profile_types(self):
        """Lists the image profile types available in the system."""
        return self._api.call("image.profile.listImageProfileTypes")

    def list_image_profiles(self):
        """Lists all the image profiles."""
        return self._api.call("image.profile.listImageProfiles")

    def get_details(self, label):
        """Returns the details of an image profile based on its label."""
        return self._api.call("image.profile.getDetails", label)

    def set_details(self, label, values):
        """Sets the label and values for an image profile."""
        return self._api.call("image.profile.setDetails", label, values)


class NamespaceImageStore:
    def __init__(self, api_test):
        self._api = api_test

    def create(self, label, uri, type, creds=None):
        """Creates a new image store."""
        if creds is None:
            creds = {}
        return self._api.call("image.store.create", label, uri, type, creds)

    def delete(self, label):
        """Deletes an image store from the system."""
        return self._api.call("image.store.delete", label)

    def list_image_store_types(self):
        """Lists the image store types available in the system."""
        return self._api.call("image.store.listImageStoreTypes")

    def list_image_stores(self):
        """Lists the image stores available in the system."""
        return self._api.call("image.store.listImageStores")

    def get_details(self, label):
        """Gets the details of an image store."""
        return self._api.call("image.store.getDetails", label)

    def set_details(self, label, details):
        """Sets the details of an image store."""
        return self._api.call("image.store.setDetails", label, details)
