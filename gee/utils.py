import datetime
import ee
from ee.ee_exception import EEException
from gee.gee_exception import GEEException
from itertools import groupby
import logging.config
from logging.handlers import RotatingFileHandler
import math
import sys
from gee.inputs import getLandsat, getS1

# Setup Logging
logger = logging.getLogger(__name__)
handler = RotatingFileHandler(
    'gee-gateway-nginx.log', maxBytes=10485760, backupCount=10)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def initialize(ee_account='', ee_key_path='', ee_user_token=''):
    try:
        if ee_account and ee_key_path:
            try:
                credentials = ee.ServiceAccountCredentials(
                    ee_account, ee_key_path)
                ee.Initialize(credentials)

            except EEException as e:
                print(str(e))
        else:
            raise Exception("EE Initialize error", "No credentials found")
    except (EEException, TypeError) as e:
        logger.error("******EE initialize error************",
                     sys.exc_info()[0])
        pass


def imageToMapId(imageName, visParams={}):
    """  """
    try:
        logger.error('******imageToMapId************')
        eeImage = ee.Image(imageName)
        mapId = eeImage.getMapId(visParams)
        logger.error('******imageToMapId complete************')
        return {
            'url': mapId['tile_fetcher'].url_format
        }
    except EEException as e:
        logger.error("******imageToMapId error************", sys.exc_info()[0])
        return {
            'errMsg': str(sys.exc_info()[0])
        }


def firstImageInMosaicToMapId(collectionName, visParams={}, dateFrom=None, dateTo=None):
    """  """
    try:
        eeCollection = ee.ImageCollection(collectionName)
        if (dateFrom and dateTo):
            eeFilterDate = ee.Filter.date(dateFrom, dateTo)
            eeCollection = eeCollection.filter(eeFilterDate)
        eeFirstImage = ee.Image(eeCollection.first())
        values = imageToMapId(eeFirstImage, visParams)
    except EEException as e:
        logger.error(
            "******firstImageInMosaicToMapId error************", sys.exc_info()[0])
        raise GEEException(sys.exc_info()[0])
    return values


def meanImageInMosaicToMapId(collectionName, visParams={}, dateFrom=None, dateTo=None):
    """  """
    try:
        eeCollection = ee.ImageCollection(collectionName)
        if (dateFrom and dateTo):
            eeFilterDate = ee.Filter.date(dateFrom, dateTo)
            eeCollection = eeCollection.filter(eeFilterDate)
        eeMeanImage = ee.Image(eeCollection.mean())
        values = imageToMapId(eeMeanImage, visParams)
    except EEException as e:
        raise GEEException(sys.exc_info()[0])
    return values


def firstCloudFreeImageInMosaicToMapId(collectionName, visParams={}, dateFrom=None, dateTo=None):
    """  """
    try:
        skipCloudMask = False
        eeCollection = ee.ImageCollection(collectionName)
        if("b2" not in visParams["bands"].lower()):
            skipCloudMask = True
        elif ("lc8" in collectionName.lower()):
            skipCloudMask = False
        elif ("le7" in collectionName.lower()):
            skipCloudMask = False
        elif ("lt5" in collectionName.lower()):
            skipCloudMask = False
        else:
            skipCloudMask = True
        if (dateFrom and dateTo):
            eeFilterDate = ee.Filter.date(dateFrom, dateTo)
            eeCollection = eeCollection.filter(eeFilterDate)
        eeFirstImage = ee.Image(eeCollection.mosaic())
        try:
            if(skipCloudMask == False):
                sID = ''
                if ("lc8" in collectionName.lower()):
                    sID = 'OLI_TIRS'
                elif ("le7" in collectionName.lower()):
                    sID = 'ETM'
                elif ("lt5" in collectionName.lower()):
                    sID = 'TM'
                scored = ee.Algorithms.Landsat.simpleCloudScore(
                    eeFirstImage.set('SENSOR_ID', sID))
                mask = scored.select(['cloud']).lte(20)
                masked = eeFirstImage.updateMask(mask)
                values = imageToMapId(masked, visParams)
            else:
                values = imageToMapId(eeFirstImage, visParams)
        except EEException as ine:
            imageToMapId(eeFirstImage, visParams)
    except EEException as e:
        raise GEEException(sys.exc_info()[0])
    return values

# Index Image Collection


def lsMaskClouds(img, cloudThresh=10):
    score = ee.Image(1.0)
    # Clouds are reasonably bright in the blue band.
    blue_rescale = img.select('blue').subtract(ee.Number(0.1)).divide(
        ee.Number(0.3).subtract(ee.Number(0.1)))
    score = score.min(blue_rescale)

    # Clouds are reasonably bright in all visible bands.
    visible = img.select('red').add(
        img.select('green')).add(img.select('blue'))
    visible_rescale = visible.subtract(ee.Number(0.2)).divide(
        ee.Number(0.8).subtract(ee.Number(0.2)))
    score = score.min(visible_rescale)

    # Clouds are reasonably bright in all infrared bands.
    infrared = img.select('nir').add(
        img.select('swir1')).add(img.select('swir2'))
    infrared_rescale = infrared.subtract(ee.Number(0.3)).divide(
        ee.Number(0.8).subtract(ee.Number(0.3)))
    score = score.min(infrared_rescale)

    # Clouds are reasonably cool in temperature.
    temp_rescale = img.select('temp').subtract(ee.Number(300)).divide(
        ee.Number(290).subtract(ee.Number(300)))
    score = score.min(temp_rescale)

    # However, clouds are not snow.
    ndsi = img.normalizedDifference(['green', 'swir1'])
    ndsi_rescale = ndsi.subtract(ee.Number(0.8)).divide(
        ee.Number(0.6).subtract(ee.Number(0.8)))
    score = score.min(ndsi_rescale).multiply(100).byte()
    mask = score.lt(cloudThresh).rename(['cloudMask'])
    img = img.updateMask(mask)
    return img.addBands(score)


def s2MaskClouds(img):
    qa = img.select('QA60')

    # Bits 10 and 11 are clouds and cirrus, respectively.
    cloudBitMask = int(math.pow(2, 10))
    cirrusBitMask = int(math.pow(2, 11))

    # clear if both flags set to zero.
    clear = qa.bitwiseAnd(cloudBitMask).eq(0).And(
        qa.bitwiseAnd(cirrusBitMask).eq(0))

    return img.divide(10000).updateMask(clear).set('system:time_start', img.get('system:time_start'))


def bandPassAdjustment(img):
    keep = img.select(['temp'])
    bands = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2']
    # linear regression coefficients for adjustment
    gain = ee.Array([[0.977], [1.005], [0.982], [1.001], [1.001], [0.996]])
    bias = ee.Array([[-0.00411], [-0.00093], [0.00094],
                    [-0.00029], [-0.00015], [-0.00097]])
    # Make an Array Image, with a 2-D Array per pixel.
    arrayImage2D = img.select(bands).toArray().toArray(1)

    # apply correction factors and reproject array to geographic image
    componentsImage = ee.Image(gain).multiply(arrayImage2D).add(ee.Image(bias)) \
        .arrayProject([0]).arrayFlatten([bands]).float()

    # .set('system:time_start',img.get('system:time_start'));
    return keep.addBands(componentsImage)


def getLandSatMergedCollection():
    eeCollection = None
    try:
        sensorBandDictLandsatTOA = {'L8': [1, 2, 3, 4, 5, 9, 6],
                                    'L7': [0, 1, 2, 3, 4, 5, 7],
                                    'L5': [0, 1, 2, 3, 4, 5, 6],
                                    'L4': [0, 1, 2, 3, 4, 5, 6],
                                    'S2': [1, 2, 3, 7, 11, 10, 12]}
        bandNamesLandsatTOA = ['blue', 'green',
                               'red', 'nir', 'swir1', 'temp', 'swir2']
        metadataCloudCoverMax = 100
        #region = ee.Geometry.Point([5.2130126953125,15.358356179450585])
        # .filterBounds(region).filterDate(iniDate,endDate)\
        lt4 = ee.ImageCollection('LANDSAT/LT4_L1T_TOA') \
            .filterMetadata('CLOUD_COVER', 'less_than', metadataCloudCoverMax) \
            .select(sensorBandDictLandsatTOA['L4'], bandNamesLandsatTOA).map(lsMaskClouds)
        lt5 = ee.ImageCollection('LANDSAT/LT5_L1T_TOA') \
            .filterMetadata('CLOUD_COVER', 'less_than', metadataCloudCoverMax) \
            .select(sensorBandDictLandsatTOA['L5'], bandNamesLandsatTOA).map(lsMaskClouds)
        le7 = ee.ImageCollection('LANDSAT/LE7_L1T_TOA') \
            .filterMetadata('CLOUD_COVER', 'less_than', metadataCloudCoverMax) \
            .select(sensorBandDictLandsatTOA['L7'], bandNamesLandsatTOA).map(lsMaskClouds)
        lc8 = ee.ImageCollection('LANDSAT/LC08/C01/T1_TOA') \
            .filterMetadata('CLOUD_COVER', 'less_than', metadataCloudCoverMax) \
            .select(sensorBandDictLandsatTOA['L8'], bandNamesLandsatTOA).map(lsMaskClouds)
        s2 = ee.ImageCollection('COPERNICUS/S2') \
            .filterMetadata('CLOUDY_PIXEL_PERCENTAGE', 'less_than', metadataCloudCoverMax) \
            .map(s2MaskClouds).select(sensorBandDictLandsatTOA['S2'], bandNamesLandsatTOA) \
            .map(bandPassAdjustment)
        eeCollection = ee.ImageCollection(
            lt4.merge(lt5).merge(le7).merge(lc8).merge(s2))
    except EEException as e:
        raise GEEException(sys.exc_info()[0])
    return eeCollection


def filteredImageNDVIToMapId(iniDate=None, endDate=None, outCollection=False):
    """  """
    def calcNDVI(img):
        return img.expression('(i.nir - i.red) / (i.nir + i.red)',  {'i': img}).rename(['NDVI']) \
            .set('system:time_start', img.get('system:time_start'))
    try:
        # ee.ImageCollection(lt4.merge(lt5).merge(le7).merge(lc8))
        eeCollection = getLandSatMergedCollection().filterDate(iniDate, endDate)
        colorPalette = 'c9c0bf,435ebf,eee8aa,006400'
        visParams = {'opacity': 1, 'max': 1,
                     'min': -1, 'palette': colorPalette}
        if outCollection:
            values = eeCollection.map(calcNDVI)
        else:
            eviImage = ee.Image(eeCollection.map(calcNDVI).mean())
            values = imageToMapId(eviImage, visParams)
    except EEException as e:
        raise GEEException(sys.exc_info()[0])
    return values


def filteredImageEVIToMapId(iniDate=None, endDate=None, outCollection=False):
    """  """
    def calcEVI(img):
        return img.expression('2.5 * (i.nir - i.red) / (i.nir + 6.0 * i.red - 7.5 * i.blue + 1)',  {'i': img}).rename(['EVI']) \
            .set('system:time_start', img.get('system:time_start'))
    try:
        # ee.ImageCollection(lt4.merge(lt5).merge(le7).merge(lc8))
        eeCollection = getLandSatMergedCollection().filterDate(iniDate, endDate)
        colorPalette = 'F5F5F5,E6D3C5,C48472,B9CF63,94BF3D,6BB037,42A333,00942C,008729,007824,004A16'
        visParams = {'opacity': 1, 'max': 1,
                     'min': -1, 'palette': colorPalette}
        if outCollection:
            values = eeCollection.map(calcEVI)
        else:
            eviImage = ee.Image(eeCollection.map(calcEVI).mean())
            values = imageToMapId(eviImage, visParams)
    except EEException as e:
        raise GEEException(sys.exc_info()[0])
    return values


def filteredImageEVI2ToMapId(iniDate=None, endDate=None, outCollection=False):
    """  """
    def calcEVI2(img):
        return img.expression('2.5 * (i.nir - i.red) / (i.nir + 2.4 * i.red + 1)',  {'i': img}).rename(['EVI2']) \
            .set('system:time_start', img.get('system:time_start'))
    try:
        # ee.ImageCollection(lt4.merge(lt5).merge(le7).merge(lc8))
        eeCollection = getLandSatMergedCollection().filterDate(iniDate, endDate)
        colorPalette = 'F5F5F5,E6D3C5,C48472,B9CF63,94BF3D,6BB037,42A333,00942C,008729,007824,004A16'
        visParams = {'opacity': 1, 'max': 1,
                     'min': -1, 'palette': colorPalette}
        if outCollection:
            values = eeCollection.map(calcEVI2)
        else:
            eviImage = ee.Image(eeCollection.map(calcEVI2).mean())
            values = imageToMapId(eviImage, visParams)
    except EEException as e:
        raise GEEException(sys.exc_info()[0])
    return values


def filteredImageNDMIToMapId(iniDate=None, endDate=None, outCollection=False):
    """  """
    def calcNDMI(img):
        return img.expression('(i.nir - i.swir1) / (i.nir + i.swir1)',  {'i': img}).rename(['NDMI']) \
            .set('system:time_start', img.get('system:time_start'))
    try:
        # ee.ImageCollection(lt4.merge(lt5).merge(le7).merge(lc8))
        eeCollection = getLandSatMergedCollection().filterDate(iniDate, endDate)
        colorPalette = '0000FE,2E60FD,31B0FD,00FEFE,50FE00,DBFE66,FEFE00,FFBB00,FF6F00,FE0000'
        visParams = {'opacity': 1, 'max': 1,
                     'min': -1, 'palette': colorPalette}
        if outCollection:
            values = eeCollection.map(calcNDMI)
        else:
            eviImage = ee.Image(eeCollection.map(calcNDMI).mean())
            values = imageToMapId(eviImage, visParams)
    except EEException as e:
        raise GEEException(sys.exc_info()[0])
    return values


def filteredImageNDWIToMapId(iniDate=None, endDate=None, outCollection=False):
    """  """
    def calcNDWI(img):
        return img.expression('(i.green - i.nir) / (i.green + i.nir)',  {'i': img}).rename(['NDWI']) \
            .set('system:time_start', img.get('system:time_start'))
    try:
        # ee.ImageCollection(lt4.merge(lt5).merge(le7).merge(lc8))
        eeCollection = getLandSatMergedCollection().filterDate(iniDate, endDate)
        colorPalette = '505050,E8E8E8,00FF33,003300'
        visParams = {'opacity': 1, 'max': 1,
                     'min': -1, 'palette': colorPalette}
        if outCollection:
            values = eeCollection.map(calcNDWI)
        else:
            eviImage = ee.Image(eeCollection.map(calcNDWI).mean())
            values = imageToMapId(eviImage, visParams)
    except EEException as e:
        raise GEEException(sys.exc_info()[0])
    return values


def filteredImageByIndexToMapId(iniDate=None, endDate=None, index='NDVI'):
    """  """
    try:
        if (index == 'NDVI'):
            values = filteredImageNDVIToMapId(iniDate, endDate)
        elif (index == 'EVI'):
            values = filteredImageEVIToMapId(iniDate, endDate)
        elif (index == 'EVI2'):
            values = filteredImageEVI2ToMapId(iniDate, endDate)
        elif (index == 'NDMI'):
            values = filteredImageNDMIToMapId(iniDate, endDate)
        elif (index == 'NDWI'):
            values = filteredImageNDWIToMapId(iniDate, endDate)
    except EEException as e:
        raise GEEException(sys.exc_info()[0])
    return values


def getTimeSeriesByCollectionAndIndex(collectionName, indexName, scale, coords=[], dateFrom=None, dateTo=None, reducer=None):
    """  """
    logger.error(
        "************getTimeSeriesByCollectionAndIndex**********************")
    try:
        geometry = None
        indexCollection = None
        if isinstance(coords[0], list):
            geometry = ee.Geometry.Polygon(coords)
        else:
            geometry = ee.Geometry.Point(coords)
        if indexName != None:
            logger.error("collection: " + collectionName +
                         " - indexName: " + indexName)
            indexCollection = ee.ImageCollection(collectionName).filterDate(
                dateFrom, dateTo).select(indexName)
        else:
            logger.error("indexName missing")
            indexCollection = ee.ImageCollection(
                collectionName).filterDate(dateFrom, dateTo)

        def getIndex(image):
            """  """
            logger.error("entered getImage")
            theReducer = None
            if(reducer == 'min'):
                theReducer = ee.Reducer.min()
            elif (reducer == 'max'):
                theReducer = ee.Reducer.max()
            else:
                theReducer = ee.Reducer.mean()
            if indexName != None:
                logger.error("had indexName: " + indexName)
                indexValue = image.reduceRegion(
                    theReducer, geometry, scale).get(indexName)
                #logger.error("had indexName: " + indexName + " and indexValue is: " + indexValue.getInfo())
            else:
                logger.error("noooooooooo indexName")
                indexValue = image.reduceRegion(theReducer, geometry, scale)
            date = image.get('system:time_start')
            indexImage = ee.Image().set(
                'indexValue', [ee.Number(date), indexValue])
            return indexImage
        logger.error("b4 map")

        def getClipped(image):
            return image.clip(geometry)
        clippedcollection = indexCollection.map(getClipped)
        indexCollection1 = clippedcollection.map(getIndex)
        logger.error("mapped")
        indexCollection2 = indexCollection1.aggregate_array('indexValue')
        logger.error("aggregated")
        values = indexCollection2.getInfo()
    except EEException as e:
        logger.error(str(e))
        raise GEEException(sys.exc_info()[0])
    return values


def aggRegion(regionList):
    """ helper function to take multiple values of region and aggregate to one value """
    values = []
    for i in range(len(regionList)):
        if i != 0:
            date = datetime.datetime.fromtimestamp(
                regionList[i][-2]/1000.).strftime("%Y-%m-%d")
            values.append([date, regionList[i][-1]])

    sort = sorted(values, key=lambda x: x[0])

    out = []
    for key, group in groupby(sort, key=lambda x: x[0][:10]):
        data = list(group)
        agg = sum(j for i, j in data if j != None)
        dates = key.split('-')
        timestamp = datetime.datetime(
            int(dates[0]), int(dates[1]), int(dates[2]))
        if agg != 0:
            out.append([int(timestamp.strftime('%s'))
                       * 1000, agg/float(len(data))])

    return out


def getTimeSeriesByIndex(indexName, scale, coords=[], dateFrom=None, dateTo=None, reducer="median"):
    """  """
    bandsByCollection = {
        'LANDSAT/LC08/C01/T1_TOA': ['B2', 'B3', 'B4', 'B5', 'B6', 'B7'],
        'LANDSAT/LC08/C01/T2_TOA': ['B2', 'B3', 'B4', 'B5', 'B6', 'B7'],
        'LANDSAT/LE07/C01/T1_TOA': ['B1', 'B2', 'B3', 'B4', 'B5', 'B7'],
        'LANDSAT/LE07/C01/T2_TOA': ['B1', 'B2', 'B3', 'B4', 'B5', 'B7'],
        'LANDSAT/LT05/C01/T1_TOA': ['B1', 'B2', 'B3', 'B4', 'B5', 'B7'],
        'LANDSAT/LT05/C01/T2_TOA': ['B1', 'B2', 'B3', 'B4', 'B5', 'B7'],
        'LANDSAT/LT04/C01/T1_TOA': ['B1', 'B2', 'B3', 'B4', 'B5', 'B7'],
        'LANDSAT/LT04/C01/T2_TOA': ['B1', 'B2', 'B3', 'B4', 'B5', 'B7']
    }
    indexes = {
        'NDVI': '(nir - red) / (nir + red)',
        'EVI': '2.5 * (nir - red) / (nir + 6.0 * red - 7.5 * blue + 1)',
        'EVI2': '2.5 * (nir - red) / (nir + 2.4 * red + 1)',
        'NDMI': '(nir - swir1) / (nir + swir1)',
        'NDWI': '(green - nir) / (green + nir)',
        'NBR': '(nir - swir2) / (nir + swir2)',
        'LSAVI': '((nir - red) / (nir + red + 0.5)) * (1 + 0.5)'
    }

    def create(name):
        """  """
        def maskClouds(image):
            """  """
            def isSet(types):
                """ https://landsat.usgs.gov/collectionqualityband """
                typeByValue = {
                    'badPixels': 15,
                    'cloud': 16,
                    'shadow': 256,
                    'snow': 1024,
                    'cirrus': 4096
                }
                anySet = ee.Image(0)
                for Type in types:
                    anySet = anySet.Or(image.select(
                        'BQA').bitwiseAnd(typeByValue[Type]).neq(0))
                return anySet
            return image.updateMask(isSet(['badPixels', 'cloud', 'shadow', 'cirrus']).Not())

        def toIndex(image):
            """  """
            bands = bandsByCollection[name]
            return image.expression(indexes[indexName], {
                'blue': image.select(bands[0]),
                'green': image.select(bands[1]),
                'red': image.select(bands[2]),
                'nir': image.select(bands[3]),
                'swir1': image.select(bands[4]),
                'swir2': image.select(bands[5]),
            }).clamp(-1, 1).rename(['index'])

        def toIndexWithTimeStart(image):
            """  """
            time = image.get('system:time_start')
            image = maskClouds(image)
            return toIndex(image).set('system:time_start', time)
        #
        if dateFrom and dateTo:
            return ee.ImageCollection(name).filterDate(dateFrom, dateTo).filterBounds(geometry).map(toIndexWithTimeStart, True)
        else:
            return ee.ImageCollection(name).filterBounds(geometry).map(toIndexWithTimeStart, True)

    def reduceRegion(image):
        """  """
        if reducer == "mean":
            reduced = image.reduceRegion(
                ee.Reducer.mean(), geometry=geometry, scale=scale, maxPixels=1e6)
        elif reducer == "min":
            reduced = image.reduceRegion(
                ee.Reducer.min(), geometry=geometry, scale=scale, maxPixels=1e6)
        elif reducer == "max":
            reduced = image.reduceRegion(
                ee.Reducer.max(), geometry=geometry, scale=scale, maxPixels=1e6)
        else:
            reduced = image.reduceRegion(
                ee.Reducer.median(), geometry=geometry, scale=scale, maxPixels=1e6)
        return ee.Feature(None, {
            'index': reduced.get('index'),
            'timeIndex': [image.get('system:time_start'), reduced.get('index')]
        })
    try:
        geometry = None
        if isinstance(coords[0], list):
            geometry = ee.Geometry.Polygon(coords)
        else:
            geometry = ee.Geometry.Point(coords)
        collection = ee.ImageCollection([])
        for name in bandsByCollection:
            collection = collection.merge(create(name))
        values = ee.ImageCollection(ee.ImageCollection(collection).sort('system:time_start').distinct('system:time_start')) \
            .map(reduceRegion) \
            .filterMetadata('index', 'not_equals', None) \
            .aggregate_array('timeIndex')
        values = values.getInfo()
    except EEException as e:
        raise GEEException(sys.exc_info()[0])
    return values


def getDegradationTileUrlByDateS1(geometry, date, visParams):
    imDate = datetime.datetime.strptime(date, "%Y-%m-%d")
    befDate = imDate - datetime.timedelta(days=1)
    aftDate = imDate + datetime.timedelta(days=1)

    if isinstance(geometry[0], list):
        geometry = ee.Geometry.Polygon(geometry)
    else:
        geometry = ee.Geometry.Point(geometry)

    sentinel1Data = getS1({
        "targetBands": ['VV', 'VH', 'VV/VH'],
        'region': geometry})

    start = befDate.strftime('%Y-%m-%d')
    end = aftDate.strftime('%Y-%m-%d')

    selectedImage = sentinel1Data.filterDate(start, end).first()

    selectedImage = ee.Image(selectedImage)

    mapparams = selectedImage.getMapId(visParams)
    return mapparams['tile_fetcher'].url_format


def getDegradationPlotsByPointS1(geometry, start, end, band):
    if isinstance(geometry[0], list):
        geometry = ee.Geometry.Polygon(geometry)
    else:
        geometry = ee.Geometry.Point(geometry)

    sentinel1Data = getS1({
        "targetBands": ['VV', 'VH', 'VV/VH'],
        'region': geometry}).filterDate(start, end)

    def myimageMapper(img):
        theReducer = ee.Reducer.mean()
        indexValue = img.reduceRegion(theReducer, geometry, 30)
        date = img.get('system:time_start')
        visParams = {'bands': ['VV', 'VH', 'ratioVVVH'],
                     'min': [-15, -25, .40], 'max': [0, -10, 1], 'gamma': 1.6}
        indexImage = ee.Image().set(
            'indexValue', [ee.Number(date), indexValue])
        return indexImage
    lsd = sentinel1Data.map(myimageMapper, True)
    indexCollection2 = lsd.aggregate_array('indexValue')
    values = indexCollection2.getInfo()
    return values


def getDegradationTileUrlByDate(geometry, date, visParams):
    imDate = datetime.datetime.strptime(date, "%Y-%m-%d")
    befDate = imDate - datetime.timedelta(days=1)
    aftDate = imDate + datetime.timedelta(days=1)

    if isinstance(geometry[0], list):
        geometry = ee.Geometry.Polygon(geometry)
    else:
        geometry = ee.Geometry.Point(geometry)
    landsatData = getLandsat({
        "start": befDate.strftime('%Y-%m-%d'),
        "end": aftDate.strftime('%Y-%m-%d'),
        "targetBands": ['RED', 'GREEN', 'BLUE', 'SWIR1', 'NIR'],
        "region": geometry,
        "sensors": {"l4": False, "l5": False, "l7": False, "l8": True}
    })

    selectedImage = landsatData.first()
    unmasked = ee.Image(selectedImage).multiply(10000).toInt16().unmask()
    mapparams = unmasked.getMapId(visParams)
    return mapparams['tile_fetcher'].url_format


def getDegradationPlotsByPoint(geometry, start, end, band, sensors):
    if isinstance(geometry[0], list):
        geometry = ee.Geometry.Polygon(geometry)
    else:
        geometry = ee.Geometry.Point(geometry)
    landsatData = getLandsat({
        "start": start,
        "end": end,
        # ['SWIR1','NIR','RED','GREEN','BLUE','SWIR2','NDFI'],
        "targetBands": [band],
        "region": geometry,
        "sensors": sensors  # {"l4": True, "l5": True, "l7": True, "l8": True}
    })

    def myimageMapper(img):
        theReducer = ee.Reducer.mean()
        indexValue = img.reduceRegion(theReducer, geometry, 30)
        date = img.get('system:time_start')
        visParams = {'bands': 'RED,GREEN,BLUE', 'min': 0, 'max': 1400}
        indexImage = ee.Image().set(
            'indexValue', [ee.Number(date), indexValue])
        return indexImage
    lsd = landsatData.map(myimageMapper, True)
    indexCollection2 = lsd.aggregate_array('indexValue')
    values = indexCollection2.getInfo()
    return values


def getFeatureCollectionTileUrl(featureCollection, field, matchID, visParams):
    fc = ee.FeatureCollection(featureCollection)
    single = fc.filter(ee.Filter.equals(field, matchID))
    Pimage = ee.Image().paint(single, 0, 2)
    iobj = Pimage.getMapId(visParams)
    return iobj['tile_fetcher'].url_format


def getStatistics(paramType, aOIPoly):
    values = {}
    if (paramType == 'basin'):
        basinFC = ee.FeatureCollection(
            'ft:1aIbTi69cXMMIm5ZvHNC67hVmhefPDLfEat15iike')
        basin = basinFC.filter(ee.Filter.eq('SubBasin', aOIPoly)).first()
        poly = basin.geometry()
    elif (paramType == 'landscape'):
        lscapeFC = ee.FeatureCollection(
            'ft:1XuZH2r-oai_knDgWiOUxyDjlHZQKsEZChOjGsTjr')
        landscape = lscapeFC.filter(ee.Filter.eq('NAME', aOIPoly)).first()
        poly = landscape.geometry()
    else:
        poly = ee.Geometry.Polygon(aOIPoly)
    elev = ee.Image('USGS/GTOPO30')
    minmaxElev = elev.reduceRegion(
        ee.Reducer.minMax(), poly, 1000, maxPixels=500000000)
    minElev = minmaxElev.get('elevation_min').getInfo()
    maxElev = minmaxElev.get('elevation_max').getInfo()
    ciesinPopGrid = ee.Image('CIESIN/GPWv4/population-count/2020')
    popDict = ciesinPopGrid.reduceRegion(
        ee.Reducer.sum(), poly, maxPixels=500000000)
    pop = popDict.get('population-count').getInfo()
    pop = int(pop)
    values = {
        'minElev': minElev,
        'maxElev': maxElev,
        'pop': pop
    }
    return values


def filteredImageCompositeToMapId(collectionName, visParams={}, dateFrom=None, dateTo=None, metadataCloudCoverMax=90, simpleCompositeVariable=60):
    """  """
    try:
        logger.error('******filteredImageCompositeToMapId************')
        eeCollection = ee.ImageCollection(collectionName)
        logger.error('******eeCollection ************')
        if (dateFrom and dateTo):
            eeFilterDate = ee.Filter.date(dateFrom, dateTo)
            eeCollection = eeCollection.filter(eeFilterDate).filterMetadata(
                'CLOUD_COVER', 'less_than', metadataCloudCoverMax)
        eeMosaicImage = ee.Algorithms.Landsat.simpleComposite(
            eeCollection, simpleCompositeVariable, 10, 40, True)
        logger.error('******eeMosaicImage************')
        values = imageToMapId(eeMosaicImage, visParams)
    except EEException as e:
        raise GEEException(sys.exc_info()[0])
    return values


def filteredSentinelComposite(visParams={}, dateFrom=None, dateTo=None, metadataCloudCoverMax=10):
    def cloudScore(img):
        def rescale(img, exp, thresholds):
            return img.expression(exp, {'img': img}).subtract(thresholds[0]).divide(thresholds[1] - thresholds[0])
        score = ee.Image(1.0)
        score = score.min(rescale(img, 'img.B2', [0.1, 0.3]))
        score = score.min(rescale(img, 'img.B4 + img.B3 + img.B2', [0.2, 0.8]))
        score = score.min(
            rescale(img, 'img.B8 + img.B11 + img.B12', [0.3, 0.8]))
        ndsi = img.normalizedDifference(['B3', 'B11'])
        return score.min(rescale(ndsi, 'img', [0.8, 0.6]))

    def cloudScoreS2(img):
        rescale = img.divide(10000)
        score = cloudScore(rescale).multiply(100).rename('cloudscore')
        return img.addBands(score)
    sentinel2 = ee.ImageCollection('COPERNICUS/S2')
    f2017s2 = sentinel2.filterDate(dateFrom, dateTo).filterMetadata(
        'CLOUDY_PIXEL_PERCENTAGE', 'less_than', metadataCloudCoverMax)
    m2017s2 = f2017s2.map(cloudScoreS2)
    m2017s3 = m2017s2.median()
    return imageToMapId(m2017s3, visParams)


def listAvailableBands(name, assetType):
    eeImage = None
    if assetType == "imageCollection":
        eeImage = ee.ImageCollection(name).first()
    else:
        eeImage = ee.Image(name)
    return {
        'bands': eeImage.bandNames().getInfo(),
        'imageName': name
    }


def filteredSentinelSARComposite(visParams, dateFrom, dateTo):
    def toNatural(img):
        return ee.Image(10).pow(img.divide(10))

    def addRatioBands(img):
        # not using angle band
        vv = img.select('VV')
        vh = img.select('VH')
        vv_vh = vv.divide(vh).rename('VV/VH')
        vh_vv = vh.divide(vv).rename('VH/VV')
        return vv.addBands(vh).addBands(vv_vh).addBands(vh_vv)

    sentinel1 = ee.ImageCollection('COPERNICUS/S1_GRD')
    sentinel1 = sentinel1.filterDate(dateFrom, dateTo) \
        .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
        .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH')) \
        .filter(ee.Filter.eq('instrumentMode', 'IW'))

    sentinel1 = sentinel1.map(toNatural)
    sentinel1 = sentinel1.map(addRatioBands)
    median = sentinel1.median()
    return imageToMapId(median, visParams)
