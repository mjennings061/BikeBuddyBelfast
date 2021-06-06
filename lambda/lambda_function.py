# -*- coding: utf-8 -*-

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.
import logging
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response

import pandas as pd
from geopy.geocoders import Nominatim
import geopandas as gpd
from shapely.geometry import Point

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

bike_parking_url = 'https://services1.arcgis.com/i8LHQZrSk9zIffRU/arcgis/rest/services/CycleParkingPublicViewer/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson'
bike_rental_url = 'https://www.belfastcity.gov.uk/getmedia/fef369b2-0b72-4be0-ab32-b24a1830fd40/BelfastBikeStations181218.csv'


class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = """
            Welcome, ask me where to find a Belfast bike or
            where to park your bike in any belfast street"""
        prompt = """
        Try asking 'where can i park my bike near Castle Street?'
        Or ask 'where can i rent a bike near Donegall Pass?'"""
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(prompt)
                .response
        )


class BikeParkingIntentHandler(AbstractRequestHandler):
    """Handler for Bike Parking Belfast Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("BikeParkingIntent")(handler_input)
    
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        # take the street name as the slot from the request input
        street_name = handler_input.request_envelope.request.intent.slots["streetName"].value.lower()
        # locate street_name on the map using geopy
        locator = Nominatim(user_agent="BelfastBikeParking")
        # get the Longitude and Latitude data from the returned datapoint
        location = locator.geocode(
            query=f"{street_name}, Belfast City Centre",
            exactly_one=True,
            country_codes='gb',
        )
        print(f"{street_name} is at Latitude = {location.latitude}, Longitude = {location.longitude}")
        
        # import belfast geoJSON cycle park
        data = gpd.read_file(bike_parking_url)
        data.set_crs(crs="EPSG:4326")   # use the CRS for the UK lat/long
        # print(f"geopandas data: {data}")
        # create a new column with lat/long converted to a metre-based CRS
        data['mpoint'] = data['geometry'].to_crs(crs="EPSG:27700")
        # create a geopandas GeoSeries using the street_name point
        point = gpd.GeoSeries(
            [Point(location.longitude, location.latitude)],
            crs="EPSG:4326"
        )
        point = point.to_crs(crs="EPSG:27700")  # convert to metre-based CRS
        # calculate the distance to all cycle parks
        data['dist'] = data['mpoint'].distance(point.iloc[0])
        # find the nearest bike park (where distance is least)
        nearest = data[data['dist'] == data['dist'].min()]
        print(f"Nearest:\n{nearest}")
        
        # open a dialog to ask if you want to know more spots nearby
        
        # "The nearest is XXX outside XXX"
        # check for missing data to tailor the response
        if nearest['Building_Business_Name'].item() is not None:
            if nearest['Street_Road_Name'].item().lower() == street_name:
                speak_output = f"""The closest bicycle parking near {street_name} is
                    on the same street, 
                    outside {nearest['Building_Business_Name'].item()}
                """
            else:
                speak_output = f"""The closest bicycle parking near {street_name} is 
                    {nearest['dist'].astype("int").item()} metres away,
                    on {nearest['Street_Road_Name'].item()}, 
                    outside {nearest['Building_Business_Name'].item()}
                """
        else:
            if nearest['Street_Road_Name'].item().lower() == street_name:
                speak_output = f"""The closest bicycle parking near {street_name} is 
                    on the same street.
                """
            else:
                speak_output = f"""The closest bicycle parking near {street_name} is 
                    {nearest['dist'].astype("int").item()} metres away,
                    on {nearest['Street_Road_Name'].item()}
                """
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class BelfastBikeLocationIntent(AbstractRequestHandler):
    """Handler for Belfast Bike Location finder."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("BelfastBikeLocationIntent")(handler_input)
        
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        # take the street name as the slot from the request input
        street_name = handler_input.request_envelope.request.intent.slots["bikeStreetName"].value.lower()
        # locate street_name on the map using geopy
        locator = Nominatim(user_agent="BelfastBikeRental")
        # get the Longitude and Latitude data from the returned datapoint
        location = locator.geocode(
            query=f"{street_name}, Belfast City Centre",
            exactly_one=True,
            country_codes='gb',
        )
        print(f"{street_name} is at Latitude = {location.latitude}, Longitude = {location.longitude}")
        # create a geopandas GeoSeries using the street_name point
        point = gpd.GeoSeries(
            [Point(location.longitude, location.latitude)],
            crs="EPSG:4326"
        ).to_crs(crs="EPSG:27700")  # convert to metre-based CRS
        
        # import the Belfast Bike dataset as a pandas dataframe
        df = pd.read_csv(bike_rental_url)
        print(df.columns)
        # convert the dataframe to a GeoDataFrame
        gdf = gpd.GeoDataFrame(
            df, geometry=gpd.points_from_xy(df.Longfitude, df.Latitude)
        ).set_crs(crs="EPSG:4326")   # use the CRS for the UK lat/long)
        gdf.to_crs(crs="EPSG:27700", inplace=1) # convert to metre-based coordinates
        print(gdf.head())
        # calculate the distance to all cycle rentals
        gdf['dist'] = gdf['geometry'].distance(point.iloc[0])
        # find the nearest bike park (where distance is least)
        nearest = gdf[gdf['dist'] == gdf['dist'].min()]
        print(f"Nearest:\n{nearest}")
        
        speak_output = f"""
            The nearest Belfast Bike station to {street_name} 
            is {nearest['dist'].astype("int").iloc[0]} metres away
            at {nearest['Location'].iloc[0]}.
        """

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "You can ask me 'where can i park my bike near Bridge Street'"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Goodbye!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )


class FallbackIntentHandler(AbstractRequestHandler):
    """Single handler for Fallback Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In FallbackIntentHandler")
        speech = "Hmm, I'm not sure. You can say Hello or Help. What would you like to do?"
        reprompt = "I didn't catch that. What can I help you with?"

        return handler_input.response_builder.speak(speech).ask(reprompt).response


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(BikeParkingIntentHandler())
sb.add_request_handler(BelfastBikeLocationIntent())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()