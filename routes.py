from flask_cors import CORS
from gee.utils import *
from gee.inputs import *
from planet.utils import *
from flask import Flask, request, jsonify, render_template, json, current_app, send_file, make_response
import logging
from logging.handlers import RotatingFileHandler
import urllib
import urllib.parse
import distutils
from distutils import util
import ast

# test
logger = logging.getLogger(__name__)
handler = RotatingFileHandler(
    'gee-gateway-nginx.log', maxBytes=10485760, backupCount=10)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

gee_gateway = Flask(__name__, instance_relative_config=True,
                    static_url_path="/static", static_folder="./static")
gee_gateway.config.from_object('config')
gee_gateway.config.from_pyfile('config.py', silent=True)
# CORS(gee_gateway)


@gee_gateway.before_request
def before():
    ee_account = current_app.config.get('EE_ACCOUNT')
    ee_key_path = current_app.config.get('EE_KEY_PATH')
    if current_app.config.get('EE_TOKEN_ENABLED'):
        if 'sepal-user' in request.headers:
            user = json.loads(request.headers['sepal-user'])
            google_tokens = user.get('googleTokens', None)
            if google_tokens:
                ee_user_token = google_tokens['accessToken']
                initialize(ee_user_token=ee_user_token,
                           ee_account=ee_account, ee_key_path=ee_key_path)
        else:
            initialize(ee_account=ee_account, ee_key_path=ee_key_path)
    else:
        initialize(ee_account=ee_account, ee_key_path=ee_key_path)
    if request.host == "localhost:8888":
        CORS(gee_gateway)


@gee_gateway.route('/', methods=['GET'])
def index():
    return render_template('index.html')


############################### CEO GeoDash ##############################

# Helper Routes


@gee_gateway.route('/getAvailableBands', methods=['POST'])
def get_available_bands():
    """ To do: add definition """
    logger.error("Debugging getAvailableBands")
    try:
        request_json = request.get_json()
        if request_json:
            image_collection_name = request_json.get('imageCollection', None)
            image_name = request_json.get('image', None)
            if image_collection_name is None:
                values = listAvailableBands(image_name, True)
            else:
                logger.error("getAvailableBands else")
                actual_name = get_actual_collection(image_collection_name)
                logger.error(actual_name + "spaces?")
                values = listAvailableBands(actual_name, False)
        else:
            raise Exception(
                "Need either image or imageCollection parameter containing the full name")
    except Exception as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


# ee.Image

@gee_gateway.route('/image', methods=['POST'])
def image():
    """ Return
    .. :quickref: Image; Get the xyz map tile url of a EE Image.
    **Example request**:
    .. code-block:: javascript
        {
            assetName: "XXX",
            visParams: {
                min: 0.0,
                max: 0.0,
                bands: "XX,XX,XX",
                gamma: 0.0,
                palette: "XX"
           }
        }

    **Example response**:
    .. code-block:: javascript
    {
       url: "https://earthengine.googleapis.com/.../maps/xxxxx-xxxxxx/tiles/{z}/{x}/{y}"
    }

    :reqheader Accept: application/json
    :<json String assetName: name of the image
    :<json Object visParams: visualization parameters
    :resheader Content-Type: application/json
    """
    try:
        jsonp = request.get_json()
        if jsonp:
            values = imageToMapId(
                jsonp.get('assetName', None),
                jsonp.get('visParams', {})
            )
        else:
            raise Exception("invalid request type, please use json")
    except Exception as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


# ee.ImageCollection

@gee_gateway.route('/imageCollection', methods=['POST'])
def imageCollection():
    """
    .. :quickref: firstImageByMosaicCollection; Get the xyz map tile url of a EE firstImageByMosaicCollection.

    **Example request**:

    .. code-block:: javascript

        {
            assetName: "XX",
            visParams: {
                min: 0.0,
                max: 0.0,
                bands: "XX,XX,XX",
                gamma: 0.0
            },
            reducer,
            startDate: "YYYY-MM-DD",
            endDate: "YYYY-MM-DD"
        }

    **Example response**:

    .. code-block:: javascript

    {
       url: "https://earthengine.googleapis.com/.../maps/xxxxx-xxxxxx/tiles/{z}/{x}/{y}"
    }

    :reqheader Accept: application/json
    :<json String collectionName: name of the image collection
    :<json Object visParams: visualization parameters
    :<json String startDate: start date
    :<json String endDate: end date
    :resheader Content-Type: application/json
    """
    try:
        if request.is_json:
            request_json = request.get_json()
            collection_name = request_json.get('collectionName', None)
            if collection_name:
                values = imageCollectionToMapId(
                    collection_name,
                    request_json.get('visParams', None),
                    request_json.get('reducer', None),
                    request_json.get('startDate', None),
                    request_json.get('endDate', None)
                )
            else:
                raise Exception("invalid request type, please use json")
        else:
            raise Exception("invalid request type, please use json")
    except Exception as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200

#!! Not actually used, but could be


@gee_gateway.route('/firstImageByMosaicCollection', methods=['POST'])
def first_image_by_mosaic_collection():
    """
    .. :quickref: firstImageByMosaicCollection; Get the xyz map tile url of a EE firstImageByMosaicCollection.

    **Example request**:

    .. code-block:: javascript

        {
            collectionName: "XX",
            visParams: {
                min: 0.0,
                max: 0.0,
                bands: "XX,XX,XX",
                gamma: 0.0
            },
            startDate: "YYYY-MM-DD",
            endDate: "YYYY-MM-DD"
        }

    **Example response**:

    .. code-block:: javascript

    {
       url: "https://earthengine.googleapis.com/.../maps/xxxxx-xxxxxx/tiles/{z}/{x}/{y}"
    }

    :reqheader Accept: application/json
    :<json String collectionName: name of the image collection
    :<json Object visParams: visualization parameters
    :<json String startDate: start date
    :<json String endDate: end date
    :resheader Content-Type: application/json
    """
    try:
        if request.is_json:
            request_json = request.get_json()
            collection_name = request_json.get('collectionName', None)
            if collection_name:
                values = firstImageInMosaicToMapId(
                    collection_name,
                    request_json.get('visParams', None),
                    request_json.get('startDate', None),
                    request_json.get('endDate', None)
                )
            else:
                raise Exception("invalid request type, please use json")
        else:
            raise Exception("invalid request type, please use json")
    except Exception as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


@gee_gateway.route('/meanImageByMosaicCollections', methods=['POST'])
def mean_image_by_mosaic_collections():
    """
    .. :quickref: meanImageByMosaicCollections; Get the xyz map tile url of a EE meanImageByMosaicCollections.

    **Example request**:

    .. code-block:: javascript

        {
            collectionName: "XX",
            visParams: {
                min: 0.0,
                max: 0.0,
                bands: "XX,XX,XX",
                gamma: 0.0
            },
            startDate: "YYYY-MM-DD",
            endDate: "YYYY-MM-DD"
        }

    **Example response**:

    .. code-block:: javascript

        {
           url: "https://earthengine.googleapis.com/.../maps/xxxxx-xxxxxx/tiles/{z}/{x}/{y}"
        }

    :reqheader Accept: application/json
    :<json String collectionName: name of the image collection
    :<json Object visParams: visualization parameters
    :<json String startDate: start date
    :<json String endDate: end date
    :resheader Content-Type: application/json
    """
    try:
        request_json = request.get_json()
        if request_json:
            collection_name = request_json.get('collectionName', None)
            if collection_name:
                values = meanImageInMosaicToMapId(
                    collection_name,
                    request_json.get('visParams', None),
                    request_json.get('startDate', None),
                    request_json.get('endDate', None)
                )
            else:
                raise Exception("invalid request type, please use json")
        else:
            raise Exception("invalid request type, please use json")
    except Exception as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


@gee_gateway.route('/cloudMaskImageByMosaicCollection', methods=['POST'])
def cloud_mask_image_by_mosaic_collection():
    """
    .. :quickref: cloudMaskImageByMosaicCollection; Get the xyz map tile url of a EE cloudMaskImageByMosaicCollection.

    **Example request**:

    .. code-block:: javascript

        {
            collectionName: "XX",
            visParams: {
                min: 0.0,
                max: 0.0,
                bands: "XX,XX,XX"
            },
            startDate: "YYYY-MM-DD",
            endDate: "YYYY-MM-DD"
        }

    **Example response**:

    .. code-block:: javascript

        {
            url: "https://earthengine.googleapis.com/.../maps/xxxxx-xxxxxx/tiles/{z}/{x}/{y}"
        }

    :reqheader Accept: application/json
    :<json String collectionName: name of the image collection
    :<json Object visParams: visualization parameters
    :<json String startDate: start date
    :<json String endDate: end date
    :resheader Content-Type: application/json
    """
    try:
        request_json = request.get_json()
        if request_json:
            collection_name = request_json.get('collectionName', None)
            if collection_name:
                values = firstCloudFreeImageInMosaicToMapId(
                    collection_name,
                    request_json.get('visParams', None),
                    request_json.get('startDate', None),
                    request_json.get('endDate', None)
                )
            else:
                raise Exception("invalid request type, please use json")
        else:
            raise Exception("invalid request type, please use json")
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


@gee_gateway.route('/ImageCollectionAsset', methods=['POST'])
def image_collection_asset():
    """
    .. :quickref: FilteredSentinel;
    .. Get the xyz map tile url of a EE Sentinel filtered ImageCollection by requested Index.

    **Example request**:

    .. code-block:: javascript

        {
            imageName: "xx",
            ImageCollectionAsset: "xx",
            visParams: {
                min: 0.0,
                max: 0.0,
                bands: "XX,XX,XX"
            }
        }

    **Example response**:

    .. code-block:: javascript

        {
            url: "https://earthengine.googleapis.com/.../maps/xxxxx-xxxxxx/tiles/{z}/{x}/{y}"
        }

    :reqheader Accept: application/json
    :<json String imageName: if requesting an image asset send the image name
    :<json String ImageCollectionAsset: if requesting an imageCollection asset send the ImageCollection Asset name
    :<json Object visParams: visParams
    :resheader Content-Type: application/json
    """
    values = {}
    try:
        request_json = request.get_json()
        if json:
            if 'imageName' in request_json:
                collection = request_json.get('imageName', '')
            else:
                collection = request_json.get('ImageCollectionAsset', '')
            vis_params = request_json.get('visParams', {})
            values = getImageCollectionAsset(collection, vis_params)
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200

# ee.ImageCollection Pre defined


def get_actual_collection(name):
    if name == "LANDSAT5":
        return "LANDSAT/LT05/C01/T1"
    elif name == "LANDSAT7":
        return "LANDSAT/LE07/C01/T1"
    elif name == "LANDSAT8":
        return "LANDSAT/LC08/C01/T1_RT"
    elif name == "Sentinel2":
        return "COPERNICUS/S2"
    else:
        return name


@gee_gateway.route('/filteredLandsat', methods=['POST'])
def filtered_landsat():
    """
    .. :quickref: FilteredSentinel;
    .. Get the xyz map tile url of a EE Sentinel filtered ImageCollection by requested Index.

    **Example request**:

    .. code-block:: javascript

        {
            startDate: "YYYY-MM-DD",
            endDate: "YYYY-MM-DD",
            cloudLessThan: nn,
            bands: "B4,B5,B3",
            min: "0.03,0.01,0.05",
            max": "0.45,0.5,0.4"
        }

    **Example response**:

    .. code-block:: javascript

        {
            url: "https://earthengine.googleapis.com/.../maps/xxxxx-xxxxxx/tiles/{z}/{x}/{y}"
        }

    :reqheader Accept: application/json
    :<json String dateFrom: start date
    :<json String dateTo: end date
    :<json String cloudLessThan: cloud filter number
    :<json String bands: bands
    :<json String min: min
    :<json String max: max
    :resheader Content-Type: application/json
    """
    values = {}
    try:
        request_json = request.get_json()
        if json:
            indexName = request_json.get('indexName', 'LANDSAT5')
            values = filteredImageCompositeToMapId(
                get_actual_collection(indexName),
                {
                    'min': request_json.get('min', '0.03,0.01,0.05'),
                    'max': request_json.get('max', '0.45,0.5,0.4'),
                    'bands': request_json.get('bands', 'B4,B5,B3')
                },
                request_json.get('startDate', None),
                request_json.get('endDate', None),
                request_json.get('cloudLessThan', 90),
                60 if indexName == 'LANDSAT7' else 50)
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


@gee_gateway.route('/filteredSentinel2', methods=['POST'])
def filtered_sentinel2():
    """
    .. :quickref: FilteredSentinel;
    .. Get the xyz map tile url of a EE Sentinel filtered ImageCollection by requested Index.

    **Example request**:

    .. code-block:: javascript

        {
            startDate: "YYYY-MM-DD",
            endDate: "YYYY-MM-DD",
            cloudLessThan: nn,
            bands: "B4,B5,B3",
            min: "0.03,0.01,0.05",
            max": "0.45,0.5,0.4"
        }

    **Example response**:

    .. code-block:: javascript

        {
            url: "https://earthengine.googleapis.com/.../maps/xxxxx-xxxxxx/tiles/{z}/{x}/{y}"
        }

    :reqheader Accept: application/json
    :<json String startDate: start date
    :<json String endDate: end date
    :<json String cloudLessThan: cloud filter number
    :<json String bands: bands
    :<json String min: min
    :<json String max: max
    :resheader Content-Type: application/json
    """
    values = {}
    try:
        request_json = request.get_json()
        if json:
            values = filteredSentinelComposite({
                'min': request_json.get('min', '0.03,0.01,0.05'),
                'max': request_json.get('max', '0.45,0.5,0.4'),
                'bands': request_json.get('bands', 'B4,B5,B3')
            },
                request_json.get('startDate', None),
                request_json.get('endDate', None),
                request_json.get('cloudLessThan', 90))
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


# Only used for institution imagery


@gee_gateway.route('/filteredSentinel2SAR', methods=['POST'])
def filtered_sentinel2_sar():
    values = {}
    try:
        request_json = request.get_json()
        if request_json:
            date_from = request_json.get('dateFrom', None)
            date_to = request_json.get('dateTo', None)
            bands = request_json.get('bands', 'VH,VV,VH/VV')
            band_min = request_json.get('min', '0')
            band_max = request_json.get('max', '0.3')
            db_value = request_json.get('dbValue', False)
            vis_params = {
                'min': band_min,
                'max': band_max,
                'bands': bands
            }
            values = filteredSentinelSARComposite(
                vis_params, db_value, date_from, date_to)
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


@gee_gateway.route('/imageCollectionByIndex', methods=['POST'])
def image_collection_by_index():
    """
    .. :quickref: ImageCollectionbyIndex; Get the xyz map tile url of a EE LANDSAT ImageCollection by requested Index.

    **Example request**:

    .. code-block:: javascript

        {
            dateFrom: "YYYY-MM-DD",
            dateTo: "YYYY-MM-DD",
            index: "xx"
        }

    **Example response**:

    .. code-block:: javascript

        {
            "https://earthengine.googleapis.com/.../maps/xxxxx-xxxxxx/tiles/{z}/{x}/{y}"
        }

    :reqheader Accept: application/json
    :<json String dateFrom: start date
    :<json String dateTo: end date
    :<json String index: index requested, ie: NDVI, EVI, etc...
    :resheader Content-Type: application/json
    """
    values = {}
    try:
        request_json = request.get_json()
        if request_json:
            date_from = request_json.get('dateFrom', None)
            if not date_from:
                date_from = None
            date_to = request_json.get('dateTo', None)
            if not date_to:
                date_to = None
            image_index = request_json.get('index', 'ndvi')
            values = filteredImageByIndexToMapId(
                date_from, date_to, image_index)
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


# ee.FeatureCollection

# TODO, this route inst really generic to any feature collections like the name suggests.
@gee_gateway.route('/getTileUrlFromFeatureCollection', methods=['POST'])
def getTileUrlFromFeatureCollection():
    values = {}
    try:
        json = request.get_json()
        if json:
            defaultVisParams = {'max': 1, 'palette': ['red']}
            assetName = json.get('assetName', None)
            field = json.get('field', 'PLOTID')
            matchID = int(json.get('matchID', None))
            visParams = json.get('visParams', defaultVisParams)
            if visParams == {}:
                visParams = defaultVisParams
            values = {
                "url": getFeatureCollectionTileUrl(assetName, field, matchID, visParams)
            }
    except GEEException as e:
        logger.error(e.message)
        values = {
            'errMsg': e.message
        }
    return jsonify(values), 200


# Planet

@gee_gateway.route('/getPlanetTile', methods=['POST', 'GET'])
def get_planet_tile():
    """ To do: add definition """
    try:
        if request.method == 'POST':
            logger.error("inside POST Planet")
            request_json = request.get_json()
            api_key = request_json.get('apiKey')
            logger.error("API: " + api_key)
            geometry = request_json.get('geometry')
            start = request_json.get('dateFrom')
            end = request_json.get('dateTo', None)
            layer_count = request_json.get('layerCount', 1)
            item_types = request_json.get(
                'itemTypes', ['PSScene3Band', 'PSScene4Band'])
            buffer = int(request_json.get('buffer', 0.5))
            add_similar = bool(distutils.util.strtobool(
                request_json.get('addsimilar', 'True')))
            values = getPlanetMapID(
                api_key, geometry, start, end, layer_count, item_types, buffer, add_similar)

        else:
            # request.args.get if get
            api_key = request.args.get('apiKey')
            geometry = json.loads(request.args.get('geometry'))
            start = request.args.get('dateFrom')
            end = request.args.get('dateTo', None)
            layer_count = int(request.args.get('layerCount', 1))
            item_types = request.args.get(
                'itemTypes', ['PSScene3Band', 'PSScene4Band'])
            buffer = int(request.args.get('buffer', 0.5))
            add_similar = bool(distutils.util.strtobool(
                request.args.get('addsimilar', 'True')))
            values = getPlanetMapID(
                api_key, geometry, start, end, layer_count, item_types, buffer, add_similar)
    except Exception as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


# Time Series

@gee_gateway.route('/timeSeriesByAsset', methods=['POST'])
def time_series_index():
    """
    .. :quickref: TimeSeries;
    .. Get the timeseries for a specific ImageCollection index, date range and a polygon OR a point

    **Example request**:

    .. code-block:: javascript

        {
            collectionName: "XX",
            graphBand: "XX"
            scale: 0.0,
            geometry: [
                [0.0, 0.0],
                [...]
            ] OR [0.0, 0.0],
            startDate: "YYYY-MM-DD",
            endDate: "YYYY-MM-DD",
            reducer: "Min"
        }

    **Example response**:

    .. code-block:: javascript

        {
            timeseries: [
                [0, 0.0],
                ...
            ]
        }

    :reqheader Accept: application/json
    :<json String collectionName: name of the image collection
    :<json String index: name of the index:  (e.g. NDVI, NDWI, NVI)
    :<json Float scale: scale in meters of the projection
    :<json Array polygon: the region over which to reduce data
    :<json String dateFrom: start date
    :<json String dateTo: end date
    :resheader Content-Type: application/json
    """
    try:
        request_json = request.get_json()
        if json:
            geometry = request_json.get('geometry', None)
            if geometry:
                # FIXME, this function is poorly names since it does not take index, originally band was stuck into indexName
                timeseries = getTimeSeriesByCollectionAndIndex(
                    request_json.get('assetName', None),
                    request_json.get('graphBand', None),
                    float(request_json.get('scale', 30)),
                    geometry,
                    request_json.get('startDate', None),
                    request_json.get('endDate', None),
                    request_json.get('reducer', 'min').lower()
                )
                values = {
                    'timeseries': timeseries
                }
            else:
                raise Exception
        else:
            raise Exception
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


@gee_gateway.route('/timeSeriesByIndex', methods=['POST'])
def time_series_index2():
    """
    .. :quickref: TimeSeries2;
    .. Get the timeseries for a specific ImageCollection index, date range and a polygon OR a point

    **Example request**:

    .. code-block:: javascript

        {
            indexName: "XX"
            scale: 0.0,
            geometry: [
                [0.0, 0.0],
                [...]
            ] OR [0.0, 0.0],
            startDate: "YYYY-MM-DD",
            endDate: "YYYY-MM-DD"
        }

    **Example response**:

    .. code-block:: javascript

        {
            timeseries: [
                [0, 0.0],
                ...
            ]
        }

    :reqheader Accept: application/json
    :<json String index: name of the index:  (e.g. NDVI, NDWI, NVI)
    :<json Float scale: scale in meters of the projection
    :<json Array polygon: the region over which to reduce data
    :<json String dateFrom: start date
    :<json String dateTo: end date
    :resheader Content-Type: application/json
    """
    values = {}
    try:
        request_json = request.get_json()
        if request_json:
            geometry = request_json.get('geometry', None)
            if geometry:
                index_name = request_json.get('indexName', 'NDVI')
                scale = float(request_json.get('scale', 30))
                startDate = request_json.get('startDate', None)
                endDate = request_json.get('endDate', None)
                timeseries = getTimeSeriesByIndex2(
                    index_name, scale, geometry, startDate, endDate, 'median')
                values = {
                    'timeseries': timeseries
                }
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


# Stats

@gee_gateway.route('/getStats', methods=['POST'])
def get_stats():
    """
    .. :quickref: getStats; Get the population and elevation for a polygon

    **Example request**:

    .. code-block:: javascript

        {
            paramType: "XX",
            paramValue: [
                [0.0, 0.0],
                [...]
            ]
        }

    **Example response**:

    .. code-block:: javascript

        {maxElev: 1230, minElev: 1230, pop: 0}

    :reqheader Accept: application/json
    :<json String paramType: basin, landscape, or ''
    :<json Array polygon: the region over which to reduce data
    :resheader Content-Type: application/json
    """
    try:
        request_json = request.get_json()
        param_type = request_json.get('paramType', None)
        param_value = request_json.get('paramValue', None)
        values = getStatistics(param_type, param_value)
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


# Degradation

@gee_gateway.route('/getImagePlotDegradation', methods=['POST'])
def get_image_plot_degradation():
    try:
        logger.error("about to get json")
        request_json = request.get_json()
        logger.error("got json")
        if request_json:
            geometry = request_json.get('geometry')
            startDate = request_json.get('startDate')
            endDate = request_json.get('endDate')
            graphBand = request_json.get('graphBand', 'NDFI')
            data_type = request_json.get('dataType', 'landsat')
            sensors = {"l4": True, "l5": True, "l7": True, "l8": True}
            if data_type == 'landsat':
                values = {
                    'timeseries': getDegradationPlotsByPoint(geometry, startDate, endDate, graphBand, sensors)
                }
            else:
                values = {
                    'timeseries': getDegradationPlotsByPointS1(geometry, startDate, endDate, graphBand)
                }
        else:
            raise Exception(
                "Need either image or imageCollection parameter containing the full name")
    except Exception as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


@gee_gateway.route('/getDegradationTileUrl', methods=['POST'])
def get_degradation_tile_url():
    try:
        request_json = request.get_json()
        if json:
            image_date = request_json.get('imageDate', None)
            geometry = request_json.get('geometry')
            stretch = request_json.get('stretch', 321)
            vis_params = {}
            if stretch == 321:
                vis_params = {'bands': 'RED,GREEN,BLUE', 'min': 0, 'max': 1400}
            elif stretch == 543:
                vis_params = {'bands': 'SWIR1,NIR,RED', 'min': 0, 'max': 7000}
            elif stretch == 453:
                vis_params = {'bands': 'NIR,SWIR1,RED', 'min': 0, 'max': 7000}
            elif stretch == "SAR":
                vis_params = {'bands': 'VV,VH,VV/VH',
                              'min': '-15,-25,.40', 'max': '0,-10,1', 'gamma': '1.6'}
            tparams = request_json.get('visParams', "")

            data_type = request_json.get('dataType', 'landsat')
            if tparams != "":
                vis_params = tparams
            if data_type == 'landsat':
                values = {
                    "url": getDegradationTileUrlByDate(geometry, image_date, vis_params)
                }
            else:
                values = {
                    "url": getDegradationTileUrlByDateS1(geometry, image_date, vis_params)
                }
        else:
            raise Exception(
                "Need either imageDate and geometry parameters")
    except Exception as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


############################### Unknown, ie not in CEO ##############################

@gee_gateway.route('/timeSeriesAssetForPoint', methods=['POST'])
def time_series_asset_for_point():
    """
    .. :quickref: TimeSeries For predefined asset; Get the timeseries for a predefined EE asset, date range and a point

    **Example request**:

    .. code-block:: javascript

        {
            point:  [0.0, 0.0],
            dateFromTimeSeries: "YYYY-MM-DD",
            dateToTimeSeries: "YYYY-MM-DD"
        }

    **Example response**:

    .. code-block:: javascript

        {
            timeseries: [
                [0, 0.0],
                ...
            ]
        }

    :reqheader Accept: application/json
    :<json Array point: the point which to reduce data
    :<json String dateFrom: start date
    :<json String dateTo: end date
    :resheader Content-Type: application/json
    """
    values = {}
    try:
        request_json = request.get_json()
        if json:
            geometry = request_json.get('point', None)
            date_from = request_json.get('dateFromTimeSeries', None)
            date_to = request_json.get('dateToTimeSeries', None)
            timeseries = getTimeSeriesAssetForPoint(
                geometry, date_from, date_to)
            print("have vals")
            values = {
                'timeseries': timeseries
            }
            print(str(values))
        else:
            logger.error("i didn't have json")
    except GEEException as e:
        logger.error(e)
        values = {
            'errMsg': e
        }
    return jsonify(values), 200


@gee_gateway.route('/getCHIRPSImage', methods=['POST'])
def get_chirps_image():
    """
    .. :quickref: getCHIRPSImage; Get the xyz map tile url of a EE CHIRPS Image.

    **Example request**:

    .. code-block:: javascript

        {
            dateFrom: "YYYY-MM-DD",
            dateTo: "YYYY-MM-DD"
        }

    **Example response**:

    .. code-block:: javascript

        {
             url: "https://earthengine.googleapis.com/.../maps/xxxxx-xxxxxx/tiles/{z}/{x}/{y}"
        }

    :reqheader Accept: application/json
    :<json String dateFrom: start date
    :<json String dateTo: end date
    :resheader Content-Type: application/json
    """
    try:
        request_json = request.get_json()
        if request_json:
            values = filteredImageInCHIRPSToMapId(
                request_json.get('dateFrom', None),
                request_json.get('dateTo', None)
            )
        else:
            raise Exception("invalid request type, please use json")
    except Exception as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


@gee_gateway.route('/timeSeriesIndex3', methods=['POST'])
def time_series_index3():
    """
    .. :quickref: TimeSeries3; Get the timeseries for a specific ImageCollection index,
    ..            date range and a polygon OR a point

    **Example request**:

    .. code-block:: javascript

        {
            collectionName: "XX",
            indexName: "XX"
            scale: 0.0,
            geometry: [
                [0.0, 0.0],
                [...]
            ] OR [0.0, 0.0],
            dateFrom: "YYYY-MM-DD",
            dateTo: "YYYY-MM-DD"
        }

    **Example response**:

    .. code-block:: javascript

        {
            timeseries: [
                [0, 0.0],
                ...
            ]
        }

    :reqheader Accept: application/json
    :<json String collectionName: name of the image collection
    :<json String index: name of the index:  (e.g. NDVI, NDWI, NVI)
    :<json Float scale: scale in meters of the projection
    :<json Array polygon: the region over which to reduce data
    :<json String dateFrom: start date
    :<json String dateTo: end date
    :resheader Content-Type: application/json
    """
    values = {}
    try:
        request_json = request.get_json()
        if request_json:
            geometry = request_json.get('polygon', None)  # deprecated
            if not geometry:
                geometry = request_json.get('geometry', None)
            if geometry:
                index_name = request_json.get('indexName', 'NDVI')
                scale = float(request_json.get('scale', 30))
                reducer = request_json.get('reducer', None)
                date_from = request_json.get('dateFrom', None)
                date_to = request_json.get('dateTo', None)
                timeseries = getTimeSeriesByIndex2(
                    index_name, scale, geometry, date_from, date_to, reducer)
                values = {
                    'timeseries': timeseries
                }
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


@gee_gateway.route('/timeSeriesForPoint', methods=['POST'])
def time_series_for_point():
    """
    .. :quickref: TimeSeries ForPoint; Get the timeseries for LANDSAT, date range and a point

    **Example request**:

    .. code-block:: javascript

        {
            point:  [0.0, 0.0],
            dateFrom: "YYYY-MM-DD",
            dateTo: "YYYY-MM-DD"
        }

    **Example response**:

    .. code-block:: javascript

        {
            timeseries: [
                [0, 0.0],
                ...
            ]
        }

    :reqheader Accept: application/json
    :<json Array point: the point which to reduce data
    :<json String dateFrom: start date
    :<json String dateTo: end date
    :resheader Content-Type: application/json
    """
    values = {}
    try:
        request_json = request.get_json()
        if request_json:
            geometry = request_json.get('point', None)
            if geometry:
                timeseries = getTimeSeriesForPoint(geometry)
                values = {
                    'timeseries': timeseries
                }
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


@gee_gateway.route('/timeSeriesIndexGet', methods=['GET'])
def time_series_index_get():
    """
    .. :quickref: TimeSeries; Get the timeseries for a specific ImageCollection index, date range and polygon

    **Example request**:

    .. code-block:: javascript

        {
            collectionName: "XX",
            indexName: "XX"
            scale: 0.0,
            polygon: [
                [0.0, 0.0],
                [...]
            ],
            dateFrom: "YYYY-MM-DD",
            dateTo: "YYYY-MM-DD"
        }

    **Example response**:

    .. code-block:: javascript

        {
            timeseries: [
                [0, 0],
                ...
            ]
        }

    :reqheader Accept: application/json
    :<json String collectionName: name of the image collection
    :<json String index: name of the index:  (e.g. NDVI, NDWI, NVI)
    :<json Float scale: scale in meters of the projection
    :<json Array polygon: the region over which to reduce data
    :<json String dateFrom: start date
    :<json String dateTo: end date
    :resheader Content-Type: application/json
    """
    try:
        polygon = ast.literal_eval(urllib.parse.unquote(
            request.args.get('polygon', None)).decode('utf8'))
        index_name = request.args.get('indexName', 'NDVI')
        scale = float(request.args.get('scale', 30))
        date_from = request.args.get('dateFromTimeSeries', None)
        date_to = request.args.get('dateToTimeSeries', None)
        reducer = request.args.get('reducer', None)
        timeseries = getTimeSeriesByIndex(
            index_name, scale, polygon, date_from, date_to, reducer)
        values = {
            'timeseries': timeseries
        }
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


@gee_gateway.route('/asterMosaic', methods=['POST'])
def aster_mosaic():
    values = {}
    try:
        request_json = request.get_json()
        if json:
            vis_params = request_json.get('visParams', None)
            date_from = request_json.get('dateFrom', None)
            date_to = request_json.get('dateTo', None)
            values = getAsterMosaic(vis_params, date_from, date_to)
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


@gee_gateway.route('/ndviChange', methods=['POST'])
def ndvi_change():
    values = {}
    try:
        request_json = request.get_json()
        if json:
            vis_params = request_json.get('visParams', None)
            year_from = request_json.get('yearFrom', None)
            year_to = request_json.get('yearTo', None)
            values = getNdviChange(vis_params, year_from, year_to)
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


@gee_gateway.route('/getLatestImage', methods=['POST'])
def get_latest_image():
    values = {}
    try:
        request_json = request.get_json()
        if request_json:
            image_collection = request_json.get(
                'imageCollection', "LANDSAT/LC08/C01/T1_TOA")
            vis_params = request_json.get(
                'visParams', {"bands": "B4,B3,B2", "max": "0.3"})
            values = getLatestImageTileUrl(image_collection, vis_params)
    except Exception as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


@gee_gateway.route('/getRangedImage', methods=['POST'])
def get_ranged_image():
    values = {}
    try:
        request_json = request.get_json()
        if request_json:
            image_collection = request_json.get(
                'imageCollection', "LANDSAT/LC08/C01/T1_TOA")
            vis_params = request_json.get(
                'visParams', {"bands": "B4,B3,B2", "max": "0.3"})
            dfrom = request_json.get('dateFrom', None)
            dto = request_json.get('dateTo', None)
            values = getRangedImageTileUrl(
                image_collection, vis_params, dfrom, dto)
    except Exception as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200

############################### TimeSync ##############################


@gee_gateway.route('/ts')
def tsIndex():
    return 'TimeSync v4.0'


@gee_gateway.route('/ts/images/<lng>/<lat>/<int:year>', methods=['GET'])
def getAllLandsatImagesForPlot(lng, lat, year):
    values = {}
    try:
        if year <= 1980:
            year = None

        values = getLandsatImages((float(lng), float(lat)), year)

    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


@gee_gateway.route('/ts/chip/<lng>/<lat>/<int:year>/<int:day>/<vis>', methods=['GET'])
def getChipForYearByTargetDay(lng, lat, year, day, vis):
    """
    get image chip for specified year for plot coordinate.
    """

    values = {}
    try:
        values = getLandsatChipForYearByTargetDay(
            (float(lng), float(lat)), year, day, vis)
        fp = urllib.request.urlopen(values.get('chip_url'))
        fname = '%s_%s.png' % (values.get('iid'), values.get('doy'))
        response = make_response(send_file(
            fp, mimetype='image/png', as_attachment=True, attachment_filename=fname))
        response.headers['doy'] = values.get('doy')
        response.headers['iid'] = values.get('iid')
        response.headers['chip_url'] = values.get('chip_url')
        return response, 200
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
        return jsonify(values), 500


@gee_gateway.route('/ts/image_chip/<lng>/<lat>/<path:iid>/<vis>/<int:size>', methods=['GET'])
def getImageChip(lng, lat, iid, vis, size=255):
    """
    get image chip for specified image

    @param
        {
            "lat":
            "lng":
            "iid": LANDSAT/LE07/C01/T1_SR/LE07_045030_20000122
            "vis":
        }
    @return
    """

    values = {}
    try:
        values = createChip(iid, (float(lng), float(lat)), vis, size)
        fp = urllib.request.urlopen(values.get('chip_url'))
        fname = '%s_%s.png' % (values.get('iid'), values.get('doy'))
        response = make_response(send_file(
            fp, mimetype='image/png', as_attachment=True, attachment_filename=fname))
        response.headers['doy'] = values.get('doy')
        response.headers['iid'] = values.get('iid')
        response.headers['chip_url'] = values.get('chip_url')
        return response, 200
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
        return jsonify(values), 500
    # return jsonify(values), 200


@gee_gateway.route('/ts/chip_url/<lng>/<lat>/<int:year>/<int:day>/<vis>', methods=['GET'])
def getChipForYearByTargetDayURL(lng, lat, year, day, vis):
    """
    get image chip for specified year for plot coordinate.
    """

    values = {}
    try:
        values = getLandsatChipForYearByTargetDay(
            (float(lng), float(lat)), year, day, vis)
        return values.get('chip_url'), 200
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
        return jsonify(values), 500


@gee_gateway.route('/ts/image_chip_url/<lng>/<lat>/<path:iid>/<vis>/<int:size>', methods=['GET'])
def getImageChipURL(lng, lat, iid, vis, size=255):
    """
    get image chip for specified image

    @param
        {
            "lat":
            "lng":
            "iid": LANDSAT/LE07/C01/T1_SR/LE07_045030_20000122
            "vis":
        }
    @return
    """

    values = {}
    try:
        values = createChip(iid, (float(lng), float(lat)), vis, size)
        return jsonify(values), 200
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
        return jsonify(values), 500
    # return jsonify(values), 200


@gee_gateway.route('/ts/image_chip_xyz/<lng>/<lat>/<path:iid>/<vis>/<int:size>', methods=['GET'])
def getImageChipXYZ(lng, lat, iid, vis, size=255):
    """
    get image chip for specified image

    @param
        {
            "lat":
            "lng":
            "iid": LANDSAT/LE07/C01/T1_SR/LE07_045030_20000122
            "vis":
        }
    @return
    """

    values = {}
    try:
        values = createChipXYZ(iid, (float(lng), float(lat)), vis, size)
        return jsonify(values), 200
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
        return jsonify(values), 500
    # return jsonify(values), 200


# TODO: refactory the next three methods
@gee_gateway.route('/ts/spectrals/<lng>/<lat>', methods=['GET'])
def getPlotSpectrals(lng, lat):
    """
    get spectral data for all the landsat images.

    @param
        {
            "lat":
            "lng":
        }
    @return
    """
    values = {}
    try:
        timeseries = getTsTimeSeriesForPoint((float(lng), float(lat)))
        values = {
            'timeseries': timeseries
        }
        return jsonify(values), 200
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
        return jsonify(values), 500


@gee_gateway.route('/ts/spectrals/year/<int:year>/<lng>/<lat>', methods=['GET'])
def getPlotSpectralsByYear(year, lng, lat):
    """
    get spectral data for all the landsat images closest to the target day

    @param
        {
            "lat":
            "lng":
        }
    @return
    """
    values = {}
    try:
        # timeseries = getTsTimeSeriesForPoint((float(lng), float(lat)))
        timeseries = getTsTimeSeriesForPointByYear(
            (float(lng), float(lat)), int(year))
        values = {
            'timeseries': timeseries
        }
        return jsonify(values), 200
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
        return jsonify(values), 500


@gee_gateway.route('/ts/spectrals/day/<int:julday>/<lng>/<lat>', methods=['GET'])
def getPlotSpectralsByJulday(julday, lng, lat):
    """
    get spectral data for all the landsat images closest to the target day

    @param
        {
            "lat":
            "lng":
        }
    @return
    """
    values = {}
    try:
        # timeseries = getTsTimeSeriesForPoint((float(lng), float(lat)))
        timeseries = getTsTimeSeriesForPointByTargetDay(
            (float(lng), float(lat)), int(julday))
        values = {
            'timeseries': timeseries
        }
        return jsonify(values), 200
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
        return jsonify(values), 500
