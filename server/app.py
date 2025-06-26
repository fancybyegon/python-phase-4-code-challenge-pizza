#!/usr/bin/env python3
import os
from flask import Flask, request, make_response, jsonify
from flask_migrate import Migrate
from flask_restful import Api, Resource
from sqlalchemy.exc import IntegrityError # Import for handling database integrity errors

# Import db and models here. db is initialized *later* with app.init_app(app).
# This prevents circular imports.
from models import db, Restaurant, Pizza, RestaurantPizza

# Define the base directory for the application
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# Configure the database URI. Uses an environment variable if set, otherwise defaults to SQLite.
DATABASE = os.environ.get("DB_URI", f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}")

# Initialize the Flask application
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False # Suppress SQLAlchemy track modifications warning
app.json.compact = False # Ensure JSON output is formatted for readability

# Initialize SQLAlchemy with the Flask application context.
# This connects the 'db' object (imported from models.py) to 'app'.
db.init_app(app)

# Initialize Flask-Migrate for database schema management
migrate = Migrate(app, db)

# Initialize Flask-RESTful for building RESTful APIs
api = Api(app)

# --- Helper Functions for Consistent API Responses ---

def make_error_response(message, status_code):
    """
    Creates a standardized JSON error response.
    Args:
        message (str): The specific error message.
        status_code (int): The HTTP status code (e.g., 404, 500).
    Returns:
        flask.Response: A Flask response object.
    """
    return make_response(jsonify({"error": message}), status_code)

def make_validation_error_response(errors, status_code=400):
    """
    Creates a standardized JSON validation error response.
    Args:
        errors (list): A list of validation error strings.
        status_code (int): The HTTP status code (default: 400 Bad Request).
    Returns:
        flask.Response: A Flask response object.
    """
    return make_response(jsonify({"errors": errors}), status_code)

# --- API Resources (Flask-RESTful) ---

# Default route for basic testing of the API
@app.route("/")
def index():
    return "<h1>Restaurant-Pizza API</h1>"

# Resource for handling GET requests to /restaurants
class Restaurants(Resource):
    def get(self):
        """
        Retrieves all restaurants from the database.
        Returns a list of restaurant objects. Serialization rules in the model
        prevent excessive nesting, providing a concise overview.
        """
        restaurants = Restaurant.query.all()
        # Use to_dict() method from SerializerMixin, applying rules to limit recursion.
        serialized_restaurants = [r.to_dict(rules=('-restaurant_pizzas',)) for r in restaurants]
        return make_response(jsonify(serialized_restaurants), 200)

api.add_resource(Restaurants, "/restaurants")

# Resource for handling GET and DELETE requests to /restaurants/<int:id>
class RestaurantByID(Resource):
    def get(self, id):
        """
        Retrieves a single restaurant by its ID.
        If found, returns the restaurant details, including a nested list of
        pizzas offered by that restaurant, along with their prices (from RestaurantPizza).
        If not found, returns a 404 error.
        """
        restaurant = Restaurant.query.get(id)
        if not restaurant:
            return make_error_response("Restaurant not found", 404)

        # Serialize the restaurant, excluding its direct 'restaurant_pizzas'
        # list to manually build the desired nested 'pizzas' data structure.
        serialized_restaurant = restaurant.to_dict(rules=('-restaurant_pizzas',))

        # Manually build the list of pizzas, including the price from the
        # RestaurantPizza association object.
        pizzas_data = []
        for rp in restaurant.restaurant_pizzas:
            pizzas_data.append({
                "id": rp.pizza.id,
                "name": rp.pizza.name,
                "ingredients": rp.pizza.ingredients,
                "price": rp.price # Crucially, get the price from the RestaurantPizza instance
            })
        serialized_restaurant['pizzas'] = pizzas_data

        return make_response(jsonify(serialized_restaurant), 200)

    def delete(self, id):
        """
        Deletes a restaurant by its ID.
        If the restaurant exists, it's deleted from the database.
        Due to 'cascade="all, delete-orphan"' on the relationship in the Restaurant model,
        all associated RestaurantPizza entries for this restaurant will also be deleted.
        Returns a 204 No Content response on successful deletion, or a 404 if not found.
        """
        restaurant = Restaurant.query.get(id)
        if not restaurant:
            return make_error_response("Restaurant not found", 404)

        try:
            db.session.delete(restaurant)
            db.session.commit()
            return make_response("", 204) # 204 No Content, indicating successful deletion
        except Exception as e:
            db.session.rollback() # Rollback changes if an error occurs during deletion
            # Generic error message for unexpected issues during delete
            return make_error_response(f"Failed to delete restaurant: {str(e)}", 500)

api.add_resource(RestaurantByID, "/restaurants/<int:id>")

# Resource for handling GET requests to /pizzas
class Pizzas(Resource):
    def get(self):
        """
        Retrieves all pizzas from the database.
        Returns a list of pizza objects. Serialization rules in the model
        prevent excessive nesting.
        """
        pizzas = Pizza.query.all()
        # Use to_dict() with serialization rules to limit recursion.
        serialized_pizzas = [p.to_dict(rules=('-restaurant_pizzas',)) for p in pizzas]
        return make_response(jsonify(serialized_pizzas), 200)

api.add_resource(Pizzas, "/pizzas")

# Resource for handling POST requests to /restaurant_pizzas
class RestaurantPizzas(Resource):
    def post(self):
        """
        Creates a new RestaurantPizza entry.
        Requires 'price', 'pizza_id', and 'restaurant_id' in the request body.
        Validates the price using the model's @validates decorator.
        Ensures both pizza and restaurant exist before creating the association.
        Returns the newly created RestaurantPizza object (with associated restaurant
        and pizza details) on success (201 Created), or appropriate error messages.
        """
        data = request.get_json()

        # Extract required data from the request body
        price = data.get("price")
        pizza_id = data.get("pizza_id")
        restaurant_id = data.get("restaurant_id")

        # 1. Basic validation: check for presence of all required fields
        if not all([price is not None, pizza_id is not None, restaurant_id is not None]):
            return make_validation_error_response(["Missing required fields: price, pizza_id, restaurant_id"])

        # 2. Check if the provided restaurant_id and pizza_id exist in the database
        restaurant = Restaurant.query.get(restaurant_id)
        pizza = Pizza.query.get(pizza_id)

        if not restaurant:
            return make_error_response("Restaurant not found", 404)
        if not pizza:
            return make_error_response("Pizza not found", 404)

        try:
            # 3. Create a new RestaurantPizza instance
            new_rp = RestaurantPizza(
                price=price,
                pizza_id=pizza_id,
                restaurant_id=restaurant_id,
            )

            # Add and commit the new entry to the database.
            # The @validates decorators in the RestaurantPizza model will
            # automatically run here when 'new_rp' is added and raise a ValueError
            # if validation fails (e.g., price is not within 1-30).
            db.session.add(new_rp)
            db.session.commit()

            # 4. Return the newly created object.
            # The to_dict() method will serialize the object, and the
            # serialize_rules in the RestaurantPizza model ensure that associated
            # restaurant and pizza details are included without causing recursion.
            return make_response(jsonify(new_rp.to_dict()), 201)

        except ValueError as e:
            # Catch validation errors specifically raised by model's @validates decorators
            db.session.rollback() # Rollback the session to undo the failed addition
            return make_validation_error_response([str(e)])
        except IntegrityError:
            # Catch database integrity errors, which can occur if:
            # - Foreign key constraints are violated (e.g., pizza_id/restaurant_id don't exist,
            #   though handled above, this is a fallback).
            # - Unique constraints are violated (e.g., trying to add a duplicate entry if one were defined).
            db.session.rollback()
            return make_validation_error_response(["A database integrity error occurred (e.g., invalid ID or duplicate entry)."])
        except Exception as e:
            # Catch any other unexpected errors during the process
            db.session.rollback()
            return make_error_response(f"An unexpected server error occurred: {str(e)}", 500)

api.add_resource(RestaurantPizzas, "/restaurant_pizzas")

# Standard entry point for running the Flask development server
if __name__ == "__main__":
    app.run(port=5555, debug=True)

