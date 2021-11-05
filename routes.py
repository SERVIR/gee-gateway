from flask_cors import CORS
from flask import Flask, request, jsonify, render_template, json, current_app
from logging import getLogger, DEBUG
from logging.handlers import RotatingFileHandler
from distutils.util import strtobool

from gee.gee_exception import GEEException
from gee.utils import initialize, listAvailableBands, imageToMapId, imageCollectionToMapId, \
    firstImageInMosaicToMapId, meanImageInMosaicToMapId, firstCloudFreeImageInMosaicToMapId, \
    filteredImageCompositeToMapId, filteredSentinelComposite, filteredSentinelSARComposite, \
    filteredImageByIndexToMapId, getFeatureCollectionTileUrl, getTimeSeriesByCollectionAndIndex, \
    getTimeSeriesByIndex, getStatistics, getDegradationPlotsByPoint, getDegradationPlotsByPointS1, \
    getDegradationTileUrlByDate, getDegradationTileUrlByDateS1
from planet.utils import getPlanetMapID

# test
logger = getLogger(__name__)
handler = RotatingFileHandler(
    'gee-gateway-nginx.log', maxBytes=10485760, backupCount=10)
logger.addHandler(handler)
logger.setLevel(DEBUG)

geeGateway = Flask(__name__, instance_relative_config=True,
                   static_url_path="/static", static_folder="./static")
geeGateway.config.from_object('config')
geeGateway.config.from_pyfile('config.py', silent=True)
# CORS(geeGateway)


@geeGateway.before_request
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
        CORS(geeGateway)


########## Helper routes ##########


@geeGateway.route('/getAvailableBands', methods=['POST'])
def getAvailableBands():
    """ To do: add definition """
    logger.error("Debugging getAvailableBands")
    try:
        requestJson = request.get_json()
        values = listAvailableBands(
            requestJson.get('assetName', None),
            requestJson.get('assetType', None)
        )
    except Exception as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200

########## ee.Image ##########


@geeGateway.route('/image', methods=['POST'])
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

########## ee.ImageCollection ##########


@geeGateway.route('/imageCollection', methods=['POST'])
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
    :<json String assetName: name of the image collection
    :<json Object visParams: visualization parameters
    :<json String startDate: start date
    :<json String endDate: end date
    :resheader Content-Type: application/json
    """
    try:
        requestJson = request.get_json()
        values = imageCollectionToMapId(
            requestJson.get('assetName', None),
            requestJson.get('visParams', None),
            requestJson.get('reducer', None),
            requestJson.get('startDate', None),
            requestJson.get('endDate', None)
        )
    except Exception as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200

#!! Not actually used, but could be


@geeGateway.route('/firstImageByMosaicCollection', methods=['POST'])
def firstImageByMosaicCollection():
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
            startDate: "YYYY-MM-DD",
            endDate: "YYYY-MM-DD"
        }

    **Example response**:

    .. code-block:: javascript

    {
       url: "https://earthengine.googleapis.com/.../maps/xxxxx-xxxxxx/tiles/{z}/{x}/{y}"
    }

    :reqheader Accept: application/json
    :<json String assetName: name of the image collection
    :<json Object visParams: visualization parameters
    :<json String startDate: start date
    :<json String endDate: end date
    :resheader Content-Type: application/json
    """
    try:
        requestJson = request.get_json()
        values = firstImageInMosaicToMapId(
            requestJson.get('assetName', None),
            requestJson.get('visParams', None),
            requestJson.get('startDate', None),
            requestJson.get('endDate', None)
        )
    except Exception as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


@geeGateway.route('/meanImageByMosaicCollections', methods=['POST'])
def meanImageByMosaicCollections():
    """
    .. :quickref: meanImageByMosaicCollections; Get the xyz map tile url of a EE meanImageByMosaicCollections.

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
            startDate: "YYYY-MM-DD",
            endDate: "YYYY-MM-DD"
        }

    **Example response**:

    .. code-block:: javascript

        {
           url: "https://earthengine.googleapis.com/.../maps/xxxxx-xxxxxx/tiles/{z}/{x}/{y}"
        }

    :reqheader Accept: application/json
    :<json String assetName: name of the image collection
    :<json Object visParams: visualization parameters
    :<json String startDate: start date
    :<json String endDate: end date
    :resheader Content-Type: application/json
    """
    try:
        requestJson = request.get_json()
        values = meanImageInMosaicToMapId(
            requestJson.get('assetName', None),
            requestJson.get('visParams', None),
            requestJson.get('startDate', None),
            requestJson.get('endDate', None)
        )
    except Exception as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


@geeGateway.route('/cloudMaskImageByMosaicCollection', methods=['POST'])
def cloudMaskImageByMosaicCollection():
    """
    .. :quickref: cloudMaskImageByMosaicCollection; Get the xyz map tile url of a EE cloudMaskImageByMosaicCollection.

    **Example request**:

    .. code-block:: javascript

        {
            assetName: "XX",
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
    :<json String assetName: name of the image collection
    :<json Object visParams: visualization parameters
    :<json String startDate: start date
    :<json String endDate: end date
    :resheader Content-Type: application/json
    """
    try:
        requestJson = request.get_json()
        values = firstCloudFreeImageInMosaicToMapId(
            requestJson.get('assetName', None),
            requestJson.get('visParams', None),
            requestJson.get('startDate', None),
            requestJson.get('endDate', None)
        )
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200

########## Pre defined ee.ImageCollection ##########


def getActualCollection(name):
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


@geeGateway.route('/filteredLandsat', methods=['POST'])
def filteredLandsat():
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
        requestJson = request.get_json()
        indexName = requestJson.get('indexName', 'LANDSAT5')
        values = filteredImageCompositeToMapId(
            getActualCollection(indexName),
            {
                'min': requestJson.get('min', '0.03,0.01,0.05'),
                'max': requestJson.get('max', '0.45,0.5,0.4'),
                'bands': requestJson.get('bands', 'B4,B5,B3')
            },
            requestJson.get('startDate', None),
            requestJson.get('endDate', None),
            requestJson.get('cloudLessThan', 90),
            60 if indexName == 'LANDSAT7' else 50
        )
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


@geeGateway.route('/filteredSentinel2', methods=['POST'])
def filteredSentinel2():
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
        requestJson = request.get_json()
        values = filteredSentinelComposite({
            'min': requestJson.get('min', '0.03,0.01,0.05'),
            'max': requestJson.get('max', '0.45,0.5,0.4'),
            'bands': requestJson.get('bands', 'B4,B5,B3')
        },
            requestJson.get('startDate', None),
            requestJson.get('endDate', None),
            requestJson.get('cloudLessThan', 90)
        )
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


# Only used for institution imagery


@geeGateway.route('/filteredSentinel2SAR', methods=['POST'])
def filteredSentinel2SAR():
    values = {}
    try:
        requestJson = request.get_json()
        values = filteredSentinelSARComposite(
            {
                'min': requestJson.get('min', '0'),
                'max': requestJson.get('max', '0.3'),
                'bands': requestJson.get('bands', 'VH,VV,VH/VV')
            },
            requestJson.get('startDate', None),
            requestJson.get('endDate', None)
        )
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


@geeGateway.route('/imageCollectionByIndex', methods=['POST'])
def imageCollectionByIndex():
    """
    .. :quickref: ImageCollectionbyIndex; Get the xyz map tile url of a EE LANDSAT ImageCollection by requested Index.

    **Example request**:

    .. code-block:: javascript

        {
            startDate: "YYYY-MM-DD",
            endDate: "YYYY-MM-DD",
            indexName: "xx"
        }

    **Example response**:

    .. code-block:: javascript

        {
            "https://earthengine.googleapis.com/.../maps/xxxxx-xxxxxx/tiles/{z}/{x}/{y}"
        }

    :reqheader Accept: application/json
    :<json String startDate: start date
    :<json String endDate: end date
    :<json String indexName: index requested, ie: NDVI, EVI, etc...
    :resheader Content-Type: application/json
    """
    values = {}
    try:
        requestJson = request.get_json()
        values = filteredImageByIndexToMapId(
            requestJson.get('startDate', None),
            requestJson.get('endDate', None),
            requestJson.get('indexName', 'ndvi')
        )
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


########## ee.FeatureCollection ##########


# TODO, this route inst really generic to any feature collections like the name suggests.
@geeGateway.route('/getTileUrlFromFeatureCollection', methods=['POST'])
def getTileUrlFromFeatureCollection():
    values = {}
    try:
        json = request.get_json()
        values = {
            "url": getFeatureCollectionTileUrl(
                json.get('assetName', None),
                json.get('field', 'PLOTID'),
                int(json.get('matchID', None)),
                {'max': 1, 'palette': ['red']} if json.get(
                    'visParams', {}) == {} else json.get('visParams', {})
            )
        }
    except GEEException as e:
        logger.error(e.message)
        values = {
            'errMsg': e.message
        }
    return jsonify(values), 200

########## Planet ##########


@geeGateway.route('/getPlanetTile', methods=['POST', 'GET'])
def getPlanetTile():
    """ To do: add definition """
    try:
        requestJson = request.get_json() if request.method == 'POST' else request.args
        values = getPlanetMapID(
            requestJson.get('apiKey'),
            requestJson.get('geometry'), requestJson.get('startDate'),
            requestJson.get('endDate', None),
            requestJson.get('layerCount', 1),
            requestJson.get('itemTypes', ['PSScene3Band', 'PSScene4Band']),
            float(requestJson.get('buffer', 0.5)),
            bool(strtobool(requestJson.get('addsimilar', 'True')))
        )
    except Exception as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200

########## Time Series ##########


@geeGateway.route('/timeSeriesByAsset', methods=['POST'])
def timeSeriesByAsset():
    """
    .. :quickref: TimeSeries;
    .. Get the timeseries for a specific ImageCollection index, date range and a polygon OR a point

    **Example request**:

    .. code-block:: javascript

        {
            assetName: "XX",
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
    :<json String assetName: name of the image collection
    :<json String index: name of the index:  (e.g. NDVI, NDWI, NVI)
    :<json Float scale: scale in meters of the projection
    :<json Array polygon: the region over which to reduce data
    :<json String startDate: start date
    :<json String endDate: end date
    :resheader Content-Type: application/json
    """
    try:
        requestJson = request.get_json()
        values = {
            'timeseries': getTimeSeriesByCollectionAndIndex(
                requestJson.get('assetName', None),
                requestJson.get('graphBand', None),
                float(requestJson.get('scale', 30)),
                requestJson.get('geometry', None),
                requestJson.get('startDate', None),
                requestJson.get('endDate', None),
                requestJson.get('reducer', 'min').lower()
            )
        }
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


@geeGateway.route('/timeSeriesByIndex', methods=['POST'])
def timeSeriesByIndex():
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
    :<json String startDate: start date
    :<json String endDate: end date
    :resheader Content-Type: application/json
    """
    values = {}
    try:
        requestJson = request.get_json()
        values = {
            'timeseries': getTimeSeriesByIndex(
                requestJson.get('indexName', 'NDVI'),
                float(requestJson.get('scale', 30)),
                requestJson.get('geometry', None),
                requestJson.get('startDate', None),
                requestJson.get('endDate', None),
                'median'
            )
        }
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200

########## Stats ##########


@geeGateway.route('/getStats', methods=['POST'])
def getStats():
    """
    .. :quickref: getStats; Get the population and elevation for a polygon

    **Example request**:

    .. code-block:: javascript

        {
            paramType: "XX",
            extent: [
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
        requestJson = request.get_json()
        values = getStatistics(
            requestJson.get('paramType', None),
            requestJson.get('extent', None)
        )
    except GEEException as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200

########## Degradation##########


@geeGateway.route('/getImagePlotDegradation', methods=['POST'])
def getImagePlotDegradation():
    try:
        requestJson = request.get_json()
        geometry = requestJson.get('geometry')
        startDate = requestJson.get('startDate')
        endDate = requestJson.get('endDate')
        graphBand = requestJson.get('graphBand', 'NDFI')
        dataType = requestJson.get('dataType', 'landsat')
        sensors = {"l4": True, "l5": True, "l7": True, "l8": True}
        if dataType == 'landsat':
            values = {
                'timeseries': getDegradationPlotsByPoint(geometry, startDate, endDate, graphBand, sensors)
            }
        else:
            values = {
                'timeseries': getDegradationPlotsByPointS1(geometry, startDate, endDate, graphBand)
            }
    except Exception as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200


@geeGateway.route('/getDegradationTileUrl', methods=['POST'])
def getDegradationTileUrl():
    try:
        requestJson = request.get_json()
        imageSate = requestJson.get('imageDate', None)
        geometry = requestJson.get('geometry')
        stretch = requestJson.get('stretch', 321)
        visParams = {}
        if stretch == 321:
            visParams = {'bands': 'RED,GREEN,BLUE', 'min': 0, 'max': 1400}
        elif stretch == 543:
            visParams = {'bands': 'SWIR1,NIR,RED', 'min': 0, 'max': 7000}
        elif stretch == 453:
            visParams = {'bands': 'NIR,SWIR1,RED', 'min': 0, 'max': 7000}
        elif stretch == "SAR":
            visParams = {'bands': 'VV,VH,VV/VH',
                         'min': '-15,-25,.40', 'max': '0,-10,1', 'gamma': '1.6'}
        degDataType = requestJson.get('degDataType', 'landsat')
        if degDataType == 'landsat':
            values = {
                "url": getDegradationTileUrlByDate(geometry, imageSate, visParams)
            }
        else:
            values = {
                "url": getDegradationTileUrlByDateS1(geometry, imageSate, visParams)
            }
    except Exception as e:
        logger.error(str(e))
        values = {
            'errMsg': str(e)
        }
    return jsonify(values), 200
