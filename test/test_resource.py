import unittest
import tempfile
from server_models.resource import Resource, ResourceStore, InvalidResourceError, InvalidResourceMapError
from server_models.vocabulary import InvalidVocabularyError

def make_tempfile():
    _, fname = tempfile.mkstemp()
    return fname

class TestResourceModel(unittest.TestCase):

    def setUp(self):
        self.letter = {
            "vocab": "http://localhost:3000/vocabularies/vangoghontology.ttl",
            "resource": "urn:vangogh:testletter",
            "typeof": "Letter",
        }
        self.paragraph = {
            "vocab": "http://localhost:3000/vocabularies/vangoghontology.ttl",
            "resource": "urn:vangogh:testletter:p.5",
            "typeof": "ParagraphInLetter"
        }

    def test_resource_cannot_be_initialized_without_parameters(self):
        error = None
        try:
            Resource()
        except InvalidResourceError as e:
            error = e
        self.assertNotEqual(error, None)

    def test_resource_canont_be_initialized_without_required_properties(self):
        error = None
        try:
            Resource({"resource": "Vincent"})
        except InvalidResourceError as e:
            error = e
        self.assertNotEqual(error, None)

    def test_resource_can_be_initialized(self):
        error = None
        try:
            resource = Resource(self.letter)
        except InvalidResourceError as e:
            error = e
        self.assertEqual(error, None)
        self.assertEqual(resource.typeof, self.letter["typeof"])
        self.assertEqual(resource.resource, self.letter["resource"])

    def test_resource_accepts_new_subresources(self):
        resource = Resource(self.letter)
        subresource = Resource(self.paragraph)
        error = None
        try:
            resource.add_subresources({"hasPart": [ subresource ]})
        except InvalidResourceError as e:
            error = e
        self.assertEqual(error, None)

class TestResourceStore(unittest.TestCase):

    def setUp(self):
        self.vocab_bad = "http://localhost:3000/vocabularies/test_ontology_invalid.ttl"
        self.vocab_none = "http://localhost:3000/vocabularies/vangoghontology.tt"
        self.vocab_url = "http://localhost:3000/vocabularies/vangoghontology.ttl"
        self.config = {
            "resource_file": make_tempfile(),
            "triple_file": make_tempfile(),
            "url_file": make_tempfile()
        }
        self.letter_map = {
            "vocab": "http://localhost:3000/vocabularies/vangoghontology.ttl",
            "resource": "urn:vangogh:testletter",
            "typeof": "Letter",
            "hasPart": [
                {
                    "resource": "urn:vangogh:testletter:p.5",
                    "typeof": "ParagraphInLetter"
                }
            ]
        }
        self.correspondence_map = {
            "vocab": "http://localhost:3000/vocabularies/vangoghontology.ttl",
            "resource": "urn:vangogh:correspondence",
            "typeof": "Correspondence",
            "hasPart": [
                {
                    "resource": "urn:vangogh:testletter",
                    "typeof": "Letter"
                }
            ]
        }
        self.collection_map = {
            "vocab": "http://localhost:3000/vocabularies/vangoghontology.ttl",
            "resource": "urn:vangogh:collection",
            "typeof": "Correspondence",
            "hasPart": [
                {
                    "resource": "urn:vangogh:testletter",
                    "typeof": "Letter"
                }
            ]
        }

    def test_resource_store_can_be_initialized(self):
        store = ResourceStore(self.config)
        self.assertEqual(store.resource_index, {})

    def test_resource_store_rejects_resource_map_with_invalid_vocabulary(self):
        resource_map = self.letter_map
        resource_map['vocab'] = self.vocab_bad
        store = ResourceStore(self.config)
        error = None
        try:
            store.register_by_map(resource_map)
        except InvalidVocabularyError as e:
            error = e
        self.assertNotEqual(error, None)

    def test_resource_store_can_extract_relations_from_map(self):
        store = ResourceStore(self.config)
        store.vocab_store.register_vocabulary(self.vocab_url)
        relations = store.get_resource_relations(self.letter_map)
        self.assertTrue("hasPart" in relations)

    def test_resource_store_accepts_valid_resource_map(self):
        store = ResourceStore(self.config)
        error = None
        try:
            store.register_by_map(self.letter_map)
        except InvalidResourceMapError as e:
            error = e
        self.assertEqual(error, None)
        self.assertTrue(store.has_resource(self.letter_map["resource"]))

    def test_resource_store_alerts_registering_known_resources(self):
        store = ResourceStore(self.config)
        response = store.register_by_map(self.letter_map)
        self.assertTrue(self.letter_map["resource"] in response["registered"])
        response = store.register_by_map(self.letter_map)
        self.assertEqual(response["registered"], [])
        self.assertTrue(self.letter_map["resource"] in response["ignored"])

    def test_resource_store_alerts_registering_known_resource_as_different_type(self):
        error = None
        store = ResourceStore(self.config)
        store.register_by_map(self.letter_map)
        self.letter_map["typeof"] = "Correspondence"
        try:
            store.register_by_map(self.letter_map)
        except InvalidResourceMapError as e:
            error = e
        self.assertNotEqual(error, None)
        self.assertEqual(error.message, "Conflicting resource types: resource urn:vangogh:testletter is already registered as type Letter and cannot be additionally registered as type Correspondence" % ())

    def test_resource_store_can_link_resource_to_multiple_parents(self):
        store = ResourceStore(self.config)
        response = store.register_by_map(self.letter_map)
        response = store.register_by_map(self.correspondence_map)
        self.assertTrue("urn:vangogh:testletter" in response["ignored"])
        self.assertTrue("urn:vangogh:correspondence" in response["registered"])
        response = store.register_by_map(self.collection_map)
        self.assertTrue("urn:vangogh:testletter" in response["ignored"])
        self.assertTrue("urn:vangogh:collection" in response["registered"])

    def test_resource_store_rejects_resource_of_unknown_type(self):
        error = None
        self.letter_map["typeof"] = "UnknownType"
        store = ResourceStore(self.config)
        try:
            store.register_by_map(self.letter_map)
        except InvalidResourceMapError as e:
            error = e
        self.assertNotEqual(error, None)
        self.assertEqual(error.message, "Illegal resource type: UnknownType")

    def test_resource_store_returns_indirectly_connected_resources(self):
        store = ResourceStore(self.config)
        store.register_by_map(self.letter_map)
        store.register_by_map(self.correspondence_map)
        resource = store.get_resource(self.correspondence_map["resource"])
        self.assertTrue("urn:vangogh:testletter:p.5" in resource.list_members())

    def test_resource_store_can_persist_data(self):
        store1 = ResourceStore(self.config)
        store1.register_by_map(self.letter_map)
        store1.dump_index()
        store2 = ResourceStore(self.config)
        self.assertEqual(store1.resource_index.keys(), store2.resource_index.keys())

