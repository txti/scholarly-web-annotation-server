from flask import g
from models.error import InvalidUsage, PermissionError

"""--------------- Parse Request Headers and Parameters ------------------"""


def get_params(request, anon_allowed=True):
    params = {}
    # print("params initialized")
    interpret_header(request.headers, params, anon_allowed)
    # print("header params parsed")
    determine_access(request, params)
    # print("access params parsed")
    determine_page_view(request, params)
    # print("page view params parsed")
    determine_annotation_type(request, params)
    # print("annotation type params parsed")
    determine_representation(request, params)
    parse_search_parameters(request, params)
    return params


"""--------------- Parse Request Headers ------------------"""


def interpret_header(headers, params, anon_allowed):
    params["view"] = determine_view_preference(headers)
    # print("\n", headers)
    try:
        # if g.get('user') and g.user.__getattribute__('username'):
        params["username"] = g.user.username
    except AttributeError:
        if not anon_allowed:
            raise PermissionError(message="Anonymous access with this method is not allowed")
        params["username"] = None  # anonymous requests for accessing public annotations
    return params


def parse_prefer_header(headers):
    prefer = {}
    if not headers.get("Prefer"):
        return prefer
    for part in headers.get("Prefer").strip().split(";"):
        key, value = part.split("=")
        prefer[key] = value.strip('"').strip("'")
    if "return" in prefer and prefer["return"] == "representation":
        prefer["view"] = prefer["include"].split("#")[1]
    return prefer


def determine_view_preference(headers):
    default_view = "PreferMinimalContainer"
    prefer = parse_prefer_header(headers)
    return prefer["view"] if "view" in prefer else default_view


"""--------------- Parse Request Parameters ------------------"""


def determine_access(request, params):
    params["access_status"] = get_access_status(request)
    if params["access_status"] and "shared" in params["access_status"]:
        get_share_permissions(request, params)


def get_access_status(request):
    status_options = ["private", "shared", "public"]
    if not request.args.get("access_status"):
        return None
    access_status = request.args.get("access_status").split(",")
    for access_level in access_status:
        if access_level not in status_options:
            raise InvalidUsage("'access_status' parameter should be either 'private', 'shared' or 'public'")
    return access_status


def get_share_permissions(request, params):
    if request.args.get("can_see"):
        params["can_see"] = request.args.get("can_see").split(",")
    if request.args.get("can_edit"):
        params["can_edit"] = request.args.get("can_edit").split(",")


def determine_page_view(request, params):
    params["page"] = 0
    page = request.args.get("page")
    if page is not None:
        params["page "] = int(page)
        params["view"] = "PreferContainedIRIs"
    iris = request.args.get("iris")
    if iris is not None:
        params["iris"] = int(iris)
        if params["iris"] == 0:
            params["view"] = "PreferContainedDescriptions"


def determine_annotation_type(request, params):
    annotation_type = request.args.get("type")
    if annotation_type is not None:
        params["type"] = annotation_type


def determine_representation(request, params):
    include = request.args.get("include_permissions")
    params["include_permissions"] = False
    if include and include == "true":
        params["include_permissions"] = True


def parse_search_parameters(request, params):
    if request.args.get("target_id"):
        params["filter"] = {"target_id": request.args.get("target_id").split(",")}
    if request.args.get("target_type"):
        params["filter"] = {"target_type": request.args.get("target_type").split(",")}
