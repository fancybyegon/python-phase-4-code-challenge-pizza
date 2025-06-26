#!/usr/bin/env python3

from app import app
from models import db, Restaurant, Pizza, RestaurantPizza

with app.app_context():
    print("Deleting existing data...")
    # Delete child records first to avoid foreign key constraint issues
    RestaurantPizza.query.delete()
    Pizza.query.delete() # Delete pizzas
    Restaurant.query.delete() # Delete restaurants
    db.session.commit()
    print("Old data deleted.")

    print("Creating restaurants...")
    shack = Restaurant(name="Karen's Pizza Shack", address='123 Pizza Lane')
    bistro = Restaurant(name="Sanjay's Pizza Bistro", address='456 Doughnut Drive')
    palace = Restaurant(name="Kiki's Pizza Palace", address='789 Cheese Street')

    db.session.add_all([shack, bistro, palace])
    db.session.commit() # Commit restaurants to get their IDs before creating RestaurantPizzas

    print("Creating pizzas...")
    cheese = Pizza(name="Margherita", ingredients="Dough, Tomato Sauce, Cheese, Basil")
    pepperoni = Pizza(name="Pepperoni Supreme", ingredients="Dough, Tomato Sauce, Cheese, Pepperoni")
    california = Pizza(name="California Veggie", ingredients="Dough, Pesto, Ricotta, Red peppers, Spinach")

    db.session.add_all([cheese, pepperoni, california])
    db.session.commit() # Commit pizzas to get their IDs

    print("Creating RestaurantPizza associations...")
    # Associate pizzas with restaurants and set prices
    rp1 = RestaurantPizza(restaurant=shack, pizza=cheese, price=12.50)
    rp2 = RestaurantPizza(restaurant=bistro, pizza=pepperoni, price=14.00)
    rp3 = RestaurantPizza(restaurant=palace, pizza=california, price=15.50)
    rp4 = RestaurantPizza(restaurant=shack, pizza=pepperoni, price=13.00) # Example: Shack also sells pepperoni
    rp5 = RestaurantPizza(restaurant=bistro, pizza=cheese, price=12.75) # Example: Bistro also sells cheese

    db.session.add_all([rp1, rp2, rp3, rp4, rp5])
    db.session.commit()

    print("Seeding done!")

