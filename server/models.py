# models.py
# Import necessary modules from SQLAlchemy
from flask_sqlalchemy import SQLAlchemy # This is needed for the db object creation
from sqlalchemy import MetaData, Column, Integer, String, Float, ForeignKey # Explicitly import Column types
from sqlalchemy.orm import validates # Used for custom validation methods on models
from sqlalchemy.ext.associationproxy import association_proxy # For simplified many-to-many access
from sqlalchemy_serializer import SerializerMixin # For easy model-to-dict serialization

# Define metadata for naming conventions, useful for auto-generated foreign key names
metadata = MetaData(
    naming_convention={
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    }
)

# Initialize SQLAlchemy DB object. This 'db' instance will be connected to the Flask app
# via db.init_app(app) in app.py. It uses the metadata defined above.
db = SQLAlchemy(metadata=metadata)

# Define the Restaurant model, inheriting from db.Model and SerializerMixin
class Restaurant(db.Model, SerializerMixin):
    __tablename__ = "restaurants" # Name of the database table

    # Define table columns
    id = Column(Integer, primary_key=True) # Primary key, auto-increments
    name = Column(String(50), unique=True, nullable=False) # Restaurant name, must be unique, not null, max 50 chars
    address = Column(String(100), nullable=False) # Restaurant address, cannot be null, max 100 chars

    # Define the one-to-many relationship with RestaurantPizza.
    # 'restaurant_pizzas' will be a list of RestaurantPizza objects associated with this restaurant.
    # 'back_populates' creates a bidirectional relationship with the 'restaurant' attribute in RestaurantPizza.
    # 'cascade='all, delete-orphan'' ensures that if a Restaurant is deleted, all its associated
    # RestaurantPizza entries are also deleted (and orphaned ones cleaned up by SQLAlchemy).
    restaurant_pizzas = db.relationship("RestaurantPizza", back_populates="restaurant", cascade="all, delete-orphan")

    # Use association_proxy to easily access Pizza objects directly from a Restaurant instance.
    # This creates a 'many-to-many' feel without explicitly defining it here.
    pizzas = association_proxy("restaurant_pizzas", "pizza")

    # Define serialization rules for `to_dict()` from SerializerMixin.
    # The rule '-restaurant_pizzas.restaurant' tells the serializer to exclude the 'restaurant'
    # attribute *within* the serialized 'restaurant_pizzas' list. This prevents infinite recursion
    # when serializing deeply nested relationships.
    serialize_rules = ("-restaurant_pizzas.restaurant",)

    # Custom validation for the 'name' attribute using SQLAlchemy's @validates decorator.
    @validates('name')
    def validate_name(self, key, name):
        if not name:
            raise ValueError("Restaurant must have a name.")
        # Ensure name length is within limits
        if not (1 <= len(name) <= 50):
            raise ValueError("Restaurant name must be between 1 and 50 characters.")
        return name # Return the validated value

    # Custom validation for the 'address' attribute.
    @validates('address')
    def validate_address(self, key, address):
        if not address:
            raise ValueError("Restaurant must have an address.")
        return address # Return the validated value

    # String representation for debugging
    def __repr__(self):
        return f"<Restaurant {self.id}: {self.name}>"

# Define the Pizza model
class Pizza(db.Model, SerializerMixin):
    __tablename__ = "pizzas" # Name of the database table

    # Define table columns
    id = Column(Integer, primary_key=True) # Primary key
    name = Column(String(50), nullable=False) # Pizza name, cannot be null, max 50 chars
    ingredients = Column(String(255), nullable=False) # Ingredients list, cannot be null, max 255 chars

    # Define the one-to-many relationship with RestaurantPizza.
    # Similar to Restaurant, this allows a Pizza to know which RestaurantPizza entries it's part of.
    # 'cascade' ensures that if a Pizza is deleted, its associated
    # RestaurantPizza entries are also deleted.
    restaurant_pizzas = db.relationship("RestaurantPizza", back_populates="pizza", cascade="all, delete-orphan")

    # Association proxy to easily access Restaurant objects directly from a Pizza instance.
    restaurants = association_proxy("restaurant_pizzas", "restaurant")

    # Serialization rules for `to_dict()`.
    # Exclude the 'pizza' attribute within 'restaurant_pizzas' to prevent recursion.
    serialize_rules = ("-restaurant_pizzas.pizza",)

    # Custom validation for the 'name' attribute.
    @validates('name')
    def validate_name(self, key, name):
        if not name:
            raise ValueError("Pizza must have a name.")
        return name # Return the validated value

    # Custom validation for the 'ingredients' attribute.
    @validates('ingredients')
    def validate_ingredients(self, key, ingredients):
        if not ingredients:
            raise ValueError("Pizza must have ingredients.")
        return ingredients # Return the validated value

    # String representation for debugging
    def __repr__(self):
        return f"<Pizza {self.id}: {self.name}, {self.ingredients}>"

# Define the RestaurantPizza model (the association table for the many-to-many relationship)
class RestaurantPizza(db.Model, SerializerMixin):
    __tablename__ = "restaurant_pizzas" # Name of the database table

    # Define table columns
    id = Column(Integer, primary_key=True) # Primary key
    price = Column(Float, nullable=False) # Price of the pizza at this specific restaurant, now Float
    # Foreign keys to link to Restaurant and Pizza tables
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    pizza_id = Column(Integer, ForeignKey("pizzas.id"), nullable=False)

    # Define the many-to-one relationship to Restaurant.
    # 'restaurant' will be the actual Restaurant object this RestaurantPizza belongs to.
    # 'back_populates' creates a bidirectional link with 'restaurant_pizzas' in the Restaurant model.
    restaurant = db.relationship("Restaurant", back_populates="restaurant_pizzas")

    # Define the many-to-one relationship to Pizza.
    # 'pizza' will be the actual Pizza object this RestaurantPizza belongs to.
    # 'back_populates' creates a bidirectional link with 'restaurant_pizzas' in the Pizza model.
    pizza = db.relationship("Pizza", back_populates="restaurant_pizzas")

    # Serialization rules for `to_dict()`.
    # When serializing a RestaurantPizza, we want to include details of the related
    # restaurant and pizza. However, to prevent recursion, we exclude their own
    # 'restaurant_pizzas' lists within those nested objects.
    serialize_rules = ("-restaurant.restaurant_pizzas", "-pizza.restaurant_pizzas")

    # Custom validation for the 'price' attribute.
    @validates("price")
    def validate_price(self, key, value):
        if not isinstance(value, (int, float)): # Check if price is a number (int or float)
            raise ValueError("Price must be a number.")
        # Ensure price is within the allowed range (between 1 and 30 inclusive)
        if not (1 <= value <= 30):
            raise ValueError("Price must be between 1 and 30 (inclusive).")
        return value # Return the validated value

    # String representation for debugging
    def __repr__(self):
        return f"<RestaurantPizza ${self.price}>"

