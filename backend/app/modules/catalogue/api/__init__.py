"""
Routeurs API du module Catalogue — produits, catégories, unités, tôles BAC.
"""
from app.modules.catalogue.api import products

routers = [products.router]

__all__ = ["products", "routers"]