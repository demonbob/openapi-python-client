import openapi_schema_pydantic as oai
import pytest

from openapi_python_client.openapi_parser.errors import ParseError

MODULE_NAME = "openapi_python_client.openapi_parser.openapi"


class TestGeneratorData:
    def test_from_dict(self, mocker):
        Model = mocker.patch(f"{MODULE_NAME}.Model")
        EndpointCollection = mocker.patch(f"{MODULE_NAME}.EndpointCollection")
        OpenAPI = mocker.patch(f"{MODULE_NAME}.oai.OpenAPI")
        openapi = OpenAPI.parse_obj.return_value

        in_dict = mocker.MagicMock()
        get_all_enums = mocker.patch(f"{MODULE_NAME}.EnumProperty.get_all_enums")

        from openapi_python_client.openapi_parser.openapi import GeneratorData

        generator_data = GeneratorData.from_dict(in_dict)

        OpenAPI.parse_obj.assert_called_once_with(in_dict)
        Model.build.assert_called_once_with(schemas=openapi.components.schemas)
        EndpointCollection.from_data.assert_called_once_with(data=openapi.paths)
        get_all_enums.assert_called_once_with()
        assert generator_data == GeneratorData(
            title=openapi.info.title,
            description=openapi.info.description,
            version=openapi.info.version,
            endpoint_collections_by_tag=EndpointCollection.from_data.return_value,
            models=Model.build.return_value,
            enums=get_all_enums.return_value,
        )

        # Test no components
        openapi.components = None
        Model.build.reset_mock()

        generator_data = GeneratorData.from_dict(in_dict)

        Model.build.assert_not_called()
        assert generator_data.models == {}


class TestModel:
    def test_build(self, mocker):
        from_data = mocker.patch(f"{MODULE_NAME}.Model.from_data")
        in_data = {1: mocker.MagicMock(), 2: mocker.MagicMock()}
        schema_1 = mocker.MagicMock()
        schema_2 = mocker.MagicMock()
        from_data.side_effect = [schema_1, schema_2]

        from openapi_python_client.openapi_parser.openapi import Model

        result = Model.build(schemas=in_data)

        from_data.assert_has_calls([mocker.call(data=value, name=name) for (name, value) in in_data.items()])
        assert result == {
            schema_1.reference.class_name: schema_1,
            schema_2.reference.class_name: schema_2,
        }

    def test_from_data(self, mocker):
        from openapi_python_client.openapi_parser.properties import Property

        in_data = oai.Schema.construct(
            title=mocker.MagicMock(),
            description=mocker.MagicMock(),
            required=["RequiredEnum"],
            properties={"RequiredEnum": mocker.MagicMock(), "OptionalDateTime": mocker.MagicMock(),},
        )
        required_property = mocker.MagicMock(autospec=Property)
        required_imports = mocker.MagicMock()
        required_property.get_imports.return_value = {required_imports}
        optional_property = mocker.MagicMock(autospec=Property)
        optional_imports = mocker.MagicMock()
        optional_property.get_imports.return_value = {optional_imports}
        property_from_data = mocker.patch(
            f"{MODULE_NAME}.property_from_data", side_effect=[required_property, optional_property],
        )
        from_ref = mocker.patch(f"{MODULE_NAME}.Reference.from_ref")

        from openapi_python_client.openapi_parser.openapi import Model

        result = Model.from_data(data=in_data, name=mocker.MagicMock())

        from_ref.assert_called_once_with(in_data.title)
        property_from_data.assert_has_calls(
            [
                mocker.call(name="RequiredEnum", required=True, data=in_data.properties["RequiredEnum"]),
                mocker.call(name="OptionalDateTime", required=False, data=in_data.properties["OptionalDateTime"]),
            ]
        )
        required_property.get_imports.assert_called_once_with(prefix="")
        optional_property.get_imports.assert_called_once_with(prefix="")
        assert result == Model(
            reference=from_ref(),
            required_properties=[required_property],
            optional_properties=[optional_property],
            relative_imports={required_imports, optional_imports,},
            description=in_data.description,
        )

    def test_from_data_parse_error_on_reference(self):
        from openapi_python_client.openapi_parser.openapi import Model

        with pytest.raises(ParseError):
            Model.from_data(data=oai.Reference.construct(), name="")


class TestEndpoint:
    def test_parse_request_form_body(self, mocker):
        ref = mocker.MagicMock()
        body = oai.RequestBody.construct(
            content={
                "application/x-www-form-urlencoded": oai.MediaType.construct(
                    media_type_schema=oai.Reference.construct(ref=ref)
                )
            }
        )
        from_ref = mocker.patch(f"{MODULE_NAME}.Reference.from_ref")

        from openapi_python_client.openapi_parser.openapi import Endpoint

        result = Endpoint.parse_request_form_body(body)

        from_ref.assert_called_once_with(ref)
        assert result == from_ref()

    def test_parse_request_form_body_no_data(self):
        body = oai.RequestBody.construct(content={})

        from openapi_python_client.openapi_parser.openapi import Endpoint

        result = Endpoint.parse_request_form_body(body)

        assert result is None

    def test_parse_multipart_body(self, mocker):
        ref = mocker.MagicMock()
        body = oai.RequestBody.construct(
            content={"multipart/form-data": oai.MediaType.construct(media_type_schema=oai.Reference.construct(ref=ref))}
        )
        from_ref = mocker.patch(f"{MODULE_NAME}.Reference.from_ref")

        from openapi_python_client.openapi_parser.openapi import Endpoint

        result = Endpoint.parse_multipart_body(body)

        from_ref.assert_called_once_with(ref)
        assert result == from_ref()

    def test_parse_multipart_body_no_data(self):
        body = oai.RequestBody.construct(content={})

        from openapi_python_client.openapi_parser.openapi import Endpoint

        result = Endpoint.parse_multipart_body(body)

        assert result is None

    def test_parse_request_json_body(self, mocker):
        schema = mocker.MagicMock()
        body = oai.RequestBody.construct(
            content={"application/json": oai.MediaType.construct(media_type_schema=schema)}
        )
        property_from_data = mocker.patch(f"{MODULE_NAME}.property_from_data")

        from openapi_python_client.openapi_parser.openapi import Endpoint

        result = Endpoint.parse_request_json_body(body)

        property_from_data.assert_called_once_with("json_body", required=True, data=schema)
        assert result == property_from_data()

    def test_parse_request_json_body_no_data(self):
        body = oai.RequestBody.construct(content={})

        from openapi_python_client.openapi_parser.openapi import Endpoint

        result = Endpoint.parse_request_json_body(body)

        assert result is None

    def test_add_body_no_data(self, mocker):
        from openapi_python_client.openapi_parser.openapi import Endpoint

        parse_request_form_body = mocker.patch.object(Endpoint, "parse_request_form_body")
        endpoint = Endpoint(
            path="path",
            method="method",
            description=None,
            name="name",
            requires_security=False,
            tag="tag",
            relative_imports={"import_3"},
        )

        endpoint._add_body(oai.Operation.construct())

        parse_request_form_body.assert_not_called()

    def test_add_body_happy(self, mocker):
        from openapi_python_client.openapi_parser.openapi import Endpoint, Reference
        from openapi_python_client.openapi_parser.properties import Property

        request_body = mocker.MagicMock()
        form_body_reference = Reference.from_ref(ref="a")
        multipart_body_reference = Reference.from_ref(ref="b")
        parse_request_form_body = mocker.patch.object(
            Endpoint, "parse_request_form_body", return_value=form_body_reference
        )
        parse_multipart_body = mocker.patch.object(
            Endpoint, "parse_multipart_body", return_value=multipart_body_reference
        )

        json_body = mocker.MagicMock(autospec=Property)
        json_body_imports = mocker.MagicMock()
        json_body.get_imports.return_value = {json_body_imports}
        parse_request_json_body = mocker.patch.object(Endpoint, "parse_request_json_body", return_value=json_body)
        import_string_from_reference = mocker.patch(
            f"{MODULE_NAME}.import_string_from_reference", side_effect=["import_1", "import_2"]
        )

        endpoint = Endpoint(
            path="path",
            method="method",
            description=None,
            name="name",
            requires_security=False,
            tag="tag",
            relative_imports={"import_3"},
        )

        endpoint._add_body(oai.Operation.construct(requestBody=request_body))

        parse_request_form_body.assert_called_once_with(request_body)
        parse_request_json_body.assert_called_once_with(request_body)
        parse_multipart_body.assert_called_once_with(request_body)
        import_string_from_reference.assert_has_calls(
            [
                mocker.call(form_body_reference, prefix="..models"),
                mocker.call(multipart_body_reference, prefix="..models"),
            ]
        )
        json_body.get_imports.assert_called_once_with(prefix="..models")
        assert endpoint.relative_imports == {"import_1", "import_2", "import_3", json_body_imports}
        assert endpoint.json_body == json_body
        assert endpoint.form_body_reference == form_body_reference
        assert endpoint.multipart_body_reference == multipart_body_reference

    def test__add_responses(self, mocker):
        from openapi_python_client.openapi_parser.openapi import Endpoint, Reference, RefResponse

        response_1_data = mocker.MagicMock()
        response_2_data = mocker.MagicMock()
        data = {
            "200": response_1_data,
            "404": response_2_data,
        }
        endpoint = Endpoint(
            path="path",
            method="method",
            description=None,
            name="name",
            requires_security=False,
            tag="tag",
            relative_imports={"import_3"},
        )
        ref_1 = Reference.from_ref(ref="ref_1")
        ref_2 = Reference.from_ref(ref="ref_2")
        response_1 = RefResponse(status_code=200, reference=ref_1)
        response_2 = RefResponse(status_code=404, reference=ref_2)
        response_from_data = mocker.patch(f"{MODULE_NAME}.response_from_data", side_effect=[response_1, response_2])
        import_string_from_reference = mocker.patch(
            f"{MODULE_NAME}.import_string_from_reference", side_effect=["import_1", "import_2"]
        )

        endpoint._add_responses(data)

        response_from_data.assert_has_calls(
            [mocker.call(status_code=200, data=response_1_data), mocker.call(status_code=404, data=response_2_data),]
        )
        import_string_from_reference.assert_has_calls(
            [mocker.call(ref_1, prefix="..models"), mocker.call(ref_2, prefix="..models"),]
        )
        assert endpoint.responses == [response_1, response_2]
        assert endpoint.relative_imports == {"import_1", "import_2", "import_3"}

    def test__add_parameters_handles_no_params(self):
        from openapi_python_client.openapi_parser.openapi import Endpoint

        endpoint = Endpoint(
            path="path", method="method", description=None, name="name", requires_security=False, tag="tag",
        )
        endpoint._add_parameters(oai.Operation.construct())  # Just checking there's no exception here

    def test__add_parameters_fail_loudly_when_location_not_supported(self, mocker):
        from openapi_python_client.openapi_parser.openapi import Endpoint

        endpoint = Endpoint(
            path="path", method="method", description=None, name="name", requires_security=False, tag="tag",
        )
        mocker.patch(f"{MODULE_NAME}.property_from_data")

        with pytest.raises(ValueError):
            endpoint._add_parameters(
                oai.Operation.construct(
                    parameters=[
                        oai.Parameter.construct(
                            name="test", required=True, param_schema=mocker.MagicMock(), param_in="cookie"
                        )
                    ]
                )
            )

    def test__add_parameters_happy(self, mocker):
        from openapi_python_client.openapi_parser.openapi import Endpoint
        from openapi_python_client.openapi_parser.properties import Property

        endpoint = Endpoint(
            path="path",
            method="method",
            description=None,
            name="name",
            requires_security=False,
            tag="tag",
            relative_imports={"import_3"},
        )
        path_prop = mocker.MagicMock(autospec=Property)
        path_prop_import = mocker.MagicMock()
        path_prop.get_imports = mocker.MagicMock(return_value={path_prop_import})
        query_prop = mocker.MagicMock(autospec=Property)
        query_prop_import = mocker.MagicMock()
        query_prop.get_imports = mocker.MagicMock(return_value={query_prop_import})
        property_from_data = mocker.patch(f"{MODULE_NAME}.property_from_data", side_effect=[path_prop, query_prop])
        path_schema = mocker.MagicMock()
        query_schema = mocker.MagicMock()
        data = oai.Operation.construct(
            parameters=[
                oai.Parameter.construct(
                    name="path_prop_name", required=True, param_schema=path_schema, param_in="path"
                ),
                oai.Parameter.construct(
                    name="query_prop_name", required=False, param_schema=query_schema, param_in="query"
                ),
                oai.Reference.construct(),  # Should be ignored
                oai.Parameter.construct(),  # Should be ignored
            ]
        )

        endpoint._add_parameters(data)

        property_from_data.assert_has_calls(
            [
                mocker.call(name="path_prop_name", required=True, data=path_schema),
                mocker.call(name="query_prop_name", required=False, data=query_schema),
            ]
        )
        path_prop.get_imports.assert_called_once_with(prefix="..models")
        query_prop.get_imports.assert_called_once_with(prefix="..models")
        assert endpoint.relative_imports == {
            "import_3",
            path_prop_import,
            query_prop_import,
        }
        assert endpoint.path_parameters == [path_prop]
        assert endpoint.query_parameters == [query_prop]

    def test_from_data(self, mocker):
        from openapi_python_client.openapi_parser.openapi import Endpoint

        path = mocker.MagicMock()
        method = mocker.MagicMock()
        _add_parameters = mocker.patch.object(Endpoint, "_add_parameters")
        _add_responses = mocker.patch.object(Endpoint, "_add_responses")
        _add_body = mocker.patch.object(Endpoint, "_add_body")
        data = oai.Operation.construct(
            description=mocker.MagicMock(),
            operationId=mocker.MagicMock(),
            security={"blah": "bloo"},
            responses=mocker.MagicMock(),
        )

        endpoint = Endpoint.from_data(data=data, path=path, method=method, tag="default")

        assert endpoint.path == path
        assert endpoint.method == method
        assert endpoint.description == data.description
        assert endpoint.name == data.operationId
        assert endpoint.requires_security
        assert endpoint.tag == "default"
        _add_parameters.assert_called_once_with(data)
        _add_responses.assert_called_once_with(data.responses)
        _add_body.assert_called_once_with(data)

        data.security = None

        endpoint = Endpoint.from_data(data=data, path=path, method=method, tag="a")

        assert not endpoint.requires_security
        assert endpoint.tag == "a"

        data.operationId = None
        with pytest.raises(ParseError):
            Endpoint.from_data(data=data, path=path, method=method, tag="a")


class TestImportStringFromReference:
    def test_import_string_from_reference_no_prefix(self, mocker):
        from openapi_python_client.openapi_parser.openapi import import_string_from_reference
        from openapi_python_client.openapi_parser.reference import Reference

        reference = mocker.MagicMock(autospec=Reference)
        result = import_string_from_reference(reference)

        assert result == f"from .{reference.module_name} import {reference.class_name}"

    def test_import_string_from_reference_with_prefix(self, mocker):
        from openapi_python_client.openapi_parser.openapi import import_string_from_reference
        from openapi_python_client.openapi_parser.reference import Reference

        prefix = mocker.MagicMock(autospec=str)
        reference = mocker.MagicMock(autospec=Reference)
        result = import_string_from_reference(reference=reference, prefix=prefix)

        assert result == f"from {prefix}.{reference.module_name} import {reference.class_name}"


class TestEndpointCollection:
    def test_from_data(self, mocker):
        from openapi_python_client.openapi_parser.openapi import Endpoint, EndpointCollection

        path_1_put = oai.Operation.construct()
        path_1_post = oai.Operation.construct(tags=["tag_2", "tag_3"])
        path_2_get = oai.Operation.construct()
        data = {
            "path_1": oai.PathItem.construct(post=path_1_post, put=path_1_put),
            "path_2": oai.PathItem.construct(get=path_2_get),
        }
        endpoint_1 = mocker.MagicMock(autospec=Endpoint, tag="default", relative_imports={"1", "2"})
        endpoint_2 = mocker.MagicMock(autospec=Endpoint, tag="tag_2", relative_imports={"2"})
        endpoint_3 = mocker.MagicMock(autospec=Endpoint, tag="default", relative_imports={"2", "3"})
        endpoint_from_data = mocker.patch.object(
            Endpoint, "from_data", side_effect=[endpoint_1, endpoint_2, endpoint_3]
        )

        result = EndpointCollection.from_data(data=data)

        endpoint_from_data.assert_has_calls(
            [
                mocker.call(data=path_1_put, path="path_1", method="put", tag="default"),
                mocker.call(data=path_1_post, path="path_1", method="post", tag="tag_2"),
                mocker.call(data=path_2_get, path="path_2", method="get", tag="default"),
            ],
        )
        assert result == {
            "default": EndpointCollection(
                "default", endpoints=[endpoint_1, endpoint_3], relative_imports={"1", "2", "3"}
            ),
            "tag_2": EndpointCollection("tag_2", endpoints=[endpoint_2], relative_imports={"2"}),
        }

    def test_from_data_errors(self, mocker):
        from openapi_python_client.openapi_parser.openapi import Endpoint, EndpointCollection, ParseError

        path_1_put = oai.Operation.construct()
        path_1_post = oai.Operation.construct(tags=["tag_2", "tag_3"])
        path_2_get = oai.Operation.construct()
        data = {
            "path_1": oai.PathItem.construct(post=path_1_post, put=path_1_put),
            "path_2": oai.PathItem.construct(get=path_2_get),
        }
        endpoint_from_data = mocker.patch.object(
            Endpoint, "from_data", side_effect=[ParseError("1"), ParseError("2"), ParseError("3")]
        )

        result = EndpointCollection.from_data(data=data)

        endpoint_from_data.assert_has_calls(
            [
                mocker.call(data=path_1_put, path="path_1", method="put", tag="default"),
                mocker.call(data=path_1_post, path="path_1", method="post", tag="tag_2"),
                mocker.call(data=path_2_get, path="path_2", method="get", tag="default"),
            ],
        )
        assert result["default"].parse_errors[0].data == "1"
        assert result["default"].parse_errors[1].data == "3"
        assert result["tag_2"].parse_errors[0].data == "2"
