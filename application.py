import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from password_strength import PasswordPolicy

from helpers import apology, login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///inventory.db")


@app.route("/")
@login_required
def index():
    """ List, filter, search and download primary inventory items"""

    user_id = session["user_id"]

    # User inventories
    user_invs = db.execute("SELECT * FROM inventories JOIN admins ON inventories.inventory_id = admins.inventory_id WHERE admin_id = ?", user_id)
    p_inv_id = db.execute("SELECT * FROM users WHERE user_id = ?", user_id)[0]["primary_inventory"]
    inv = db.execute("SELECT * FROM items JOIN categories ON item_category_id = category_id WHERE inventory_id = ?", p_inv_id)

    invs = []
    p_inv = {}
    p_inv_value = 0

    for i in range(len(inv)):
        p_inv_value += int(inv[i]['amount']) * int(inv[i]['unit_price'])

    for i in range(len(user_invs)):
        if user_invs[i]["inventory_id"] == p_inv_id:
            active = "active"
            p_inv = [{"id": user_invs[i]["inventory_id"], "name": user_invs[i]["inventory_name"], "address": user_invs[i]["inventory_address"], "currency": user_invs[i]["inventory_currency"], "value": p_inv_value}]
        else:
            active = ""

        invs.append({"id": user_invs[i]["inventory_id"], "name": user_invs[i]["inventory_name"], "active": active, "address": user_invs[i]["inventory_address"], "currency": user_invs[i]["inventory_currency"]})


    # User categories
    u_invs = db.execute ("SELECT * FROM admins WHERE admin_id = ? AND admin_role in ('Admin', 'Editor')", user_id)

    p_cats = 0

    ids = []

    for i in range(len(u_invs)):
        ids.append(u_invs[i]['inventory_id'])


    if len(ids) <= 1:
        if len(ids) == 0:
            ids = 0
        else:
            ids = ids[0]
        cats = db.execute("SELECT * FROM categories WHERE inventory_id = ?", ids)


    else:
        ids = tuple(ids)
        cats = db.execute(f"SELECT * FROM categories WHERE inventory_id IN {ids}")

    for i in range(len(cats)):
        if cats[i]["inventory_id"] == p_inv[0]["id"]:
            p_cats += 1

    # Set to use later
    session["invs"] = invs
    session["p_inv"] = p_inv
    session["inv"] = inv
    session["cats"] = cats

    return render_template("index.html", invs=invs, p_inv=p_inv, inv=inv, p=len(inv), cats=cats, q=len(cats), count=p_cats)


@app.route("/inventory/<int:inv_id>")
@login_required
def swich_to(inv_id):
    """ Swich to another inventory"""

    user_id = session["user_id"]
    inv_name = db.execute("SELECT inventory_name FROM inventories WHERE inventory_id = ?", inv_id)[0]["inventory_name"]
    admin_id_t = db.execute("SELECT admin_id FROM admins WHERE inventory_id = ?", inv_id)
    p_inv_id = session["p_inv"][0]["id"]

    flag = 0
    if inv_id == p_inv_id:
        pass

    else:
        for i in range(len(admin_id_t)):
            if admin_id_t[i]["admin_id"] == user_id:
                db.execute("UPDATE users SET primary_inventory = ? WHERE user_id = ?",
                           inv_id, user_id)
                flag = 1
                break

        # Not admin or no such inventory (security check)
        if flag == 0:
            flash("Access denied!", "alert-danger")

    return redirect("/")


@app.route("/add-item", methods=["GET", "POST"])
@login_required
def add_item():
    """ add items to category """

    if request.method == "POST":

        # Basic info
        user_id = session["user_id"]
        primary_inventory = session["p_inv"][0]["id"]
        f = request.form

        # Ensure item name at least submitted
        if not f.get("item-name").strip():
           flash("Item name is missing", "alert-danger")

        else:
            # Submitted data
            item_category_id = f.get("item-category")
            item_name = f.get("item-name")
            manifacturer = f.get("manifacturer")
            color = f.get("color")
            unit_price = f.get("unit-price")
            unit_weight = f.get("unit-weight")
            wt_unit = f.get("wt-unit")
            length = f.get("length")
            width = f.get("width")
            height = f.get("height")
            length_unit = f.get("length-unit")
            storage_place = f.get("storage-place")
            amount = f.get("amount")
            min_amount = f.get("min-amount")
            note1 = f.get("note1")
            note2 = f.get("note2")
            note3 = f.get("note3")

            if not f.get("unit-price"):
                unit_price = 0

            if not f.get("amount"):
                amount = 0

            if not f.get("min-amount"):
                min_amount = 0


            # Insert submitted data into the database
            db.execute("INSERT INTO items (item_creator_id, item_category_id, item_name, manifacturer, color, unit_price, unit_weight, wt_unit, length, width, height, length_unit, storage_place, amount, min_amount, note1, note2, note3) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       user_id, item_category_id, item_name, manifacturer, color, unit_price, unit_weight, wt_unit, length, width, height, length_unit, storage_place, amount, min_amount, note1, note2, note3)

            p_inv_id = db.execute("SELECT * FROM users WHERE user_id = ?", user_id)[0]["primary_inventory"]

            inv = db.execute("SELECT * FROM items JOIN categories ON item_category_id = category_id WHERE inventory_id = ?", p_inv_id)

            session["inv"] = inv
            flash("Added successfuly", "alert-success")
        return redirect("/add-item")

    else:
        invs = session["invs"]
        p_inv = session["p_inv"]
        cats = session["cats"]
        return render_template("add_item.html", invs=invs, n=len(invs), p_inv=p_inv, cats=cats, q=len(cats))


@app.route("/add-category", methods=["GET", "POST"])
@login_required
def add_category():
    """ Add category to inventory """

    if request.method == "POST":

        f = request.form

        # Ensure role name at least submitted
        if not f.get("category-name").strip():
           flash("Category name is missing", "alert-danger")

        else:
            user_id = session["user_id"]

            # Submitted data
            inventory_id = f.get("inventory")
            category_name = f.get("category-name")
            about_items = f.get("about-items")

            # Insert submitted data into the database
            db.execute("INSERT INTO categories (category_creator_id, inventory_id, category_name, about_items) VALUES (?, ?, ?, ?)",
                       user_id, inventory_id, category_name, about_items)

            # Update session data
            u_cats = db.execute ("SELECT * FROM admins WHERE admin_id = ? AND admin_role in ('Admin', 'Editor')", user_id)

            ids = []

            for i in range(len(u_cats)):
                ids.append(u_cats[i]['inventory_id'])

            if len(ids) <= 1:
                if len(ids) == 0:
                    ids = 0
                else:
                    ids = ids[0]
                cats = db.execute("SELECT * FROM categories WHERE inventory_id = ?", ids)

            else:
                ids = tuple(ids)

                cats = db.execute(f"SELECT * FROM categories WHERE inventory_id IN {ids}")

            session["cats"] = cats

            flash("Category added successfully", "alert-success")

        return redirect("/add-category")

    else:
        invs = session["invs"]
        p_inv = session["p_inv"]
        return render_template("add_category.html", invs=invs, n=len(invs), p_inv=p_inv)


@app.route("/add-inventory", methods=["GET", "POST"])
@login_required
def add_inventory():
    if request.method == "POST":
        inventories = []
        invs = session['invs']
        for inv in invs:
            inventories.append(inv["name"])

        if not request.form.get("inventory-name").strip():
            flash("Inventory name is missing!", "alert-danger")
            return redirect("/add-inventory")


        elif request.form.get("inventory-name") in inventories:
                flash("One of your inventories has the same name", "alert-danger")
                return redirect("/add-inventory")
        else:

            user_id = session["user_id"]
            inventory_name = request.form.get("inventory-name")
            inventory_address = request.form.get("inventory-address")
            inventory_currency = request.form.get("inventory-currency")
            if not inventory_currency:
                inventory_currency = "USD"

            db.execute("INSERT INTO inventories (inventory_creator_id, inventory_name, inventory_address, inventory_currency) VALUES (?, ?, ?, ?)",
                        user_id, inventory_name, inventory_address, inventory_currency)


            inventory_id = db.execute("SELECT inventory_id FROM inventories WHERE inventory_name = ? AND inventory_creator_id = ?",
                                        inventory_name, user_id)[0]["inventory_id"]

            # Assign user as admin
            db.execute("INSERT INTO admins (inventory_id, admin_id, admin_role) VALUES (?, ?, ?)",
                        inventory_id, user_id, "Admin" )

            # make primary
            db.execute("UPDATE users SET primary_inventory = ? WHERE user_id = ?",
                        inventory_id, user_id)

            return redirect("/")

    else:
        invs = session["invs"]
        p_inv = session["p_inv"]
        return render_template("add_inventory.html", invs=invs, p_inv=p_inv)


@app.route("/edit-item", methods=["GET", "POST"])
@login_required
def choose_item():

    invs = session["invs"]
    p_inv = session["p_inv"]
    cats = session["cats"]
    inv = session["inv"]

    if request.method == "POST":
        f = request.form
        if not f.get("item"):
            flash("Please, select item first","alert-danger")
            redirect("/choose_item")
        elif int(f.get("item")) not in [i['item_id'] for i in inv]:
            flash("Permission denied!", "alert-danger")
            redirect("/edit-item")
        else:
            link = "/edit-item/" + f.get("item")
            return redirect(link)
    else:
        return render_template("choose_item.html", invs=invs, p_inv=p_inv, cats=cats, inv=inv)


@app.route("/edit-category", methods=["GET", "POST"])
@login_required
def choose_category():

    invs = session["invs"]
    p_inv = session["p_inv"]
    cats = session["cats"]

    if request.method == "POST":

        if request.method == "POST":
            f = request.form
            if not f.get("category"):
                flash("Please, select category first","alert-danger")
                redirect("/choose_category")
            elif int(f.get("category")) not in [i['category_id'] for i in cats]:
                flash("Permission denied!", "alert-danger")
                redirect("/edit-inventory")
            else:
                link = "/edit-category/" + f.get("category")
                return redirect(link)

    else:
        return render_template("choose_category.html", invs=invs, p_inv=p_inv, cats=cats)


@app.route("/edit-inventory", methods=["GET", "POST"])
@login_required
def choose_inventory():

    invs = session["invs"]
    p_inv = session["p_inv"]

    if request.method == "POST":
        f = request.form
        if not f.get("inventory"):
            flash("Please, select inventory first","alert-danger")
            redirect("/choose_inventory")
        elif int(f.get("inventory")) not in [i['id'] for i in invs]:
            flash("Permission denied!", "alert-danger")
            redirect("/edit-inventory")
        else:
            link = "/edit-inventory/" + f.get("inventory")
            return redirect(link)

    else:
        return render_template("choose_inventory.html", invs=invs, n=len(invs), p_inv=p_inv)


@app.route("/edit-item/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_item(item_id):

    user_id = session["user_id"]
    invs = session["invs"]
    p_inv = session["p_inv"]
    cats = session["cats"]
    inv = session["inv"]

    if request.method == "POST":

        f = request.form

        # Ensure user has permission
        if item_id not in [i['item_id'] for i in inv]:
            flash("permission denied!", "alert-danger")
            return redirect("/edit-item")

        # Ensure item name at least submitted
        elif not f.get("item-name").strip():
            flash("Item name is missing", "alert-danger")
            link = "/edit-item/" + item_id
            return redirect(link)

        else:
            # Submitted data
            item_category_id = f.get("item-category")
            item_name = f.get("item-name")
            manifacturer = f.get("manifacturer")
            color = f.get("color")
            unit_price = f.get("unit-price")
            unit_weight = f.get("unit-weight")
            wt_unit = f.get("wt-unit")
            length = f.get("length")
            width = f.get("width")
            height = f.get("height")
            length_unit = f.get("length-unit")
            storage_place = f.get("storage-place")
            amount = f.get("amount")
            min_amount = f.get("min-amount")
            note1 = f.get("note1")
            note2 = f.get("note2")
            note3 = f.get("note3")

            if not f.get("unit-price"):
                unit_price = 0

            if not f.get("amount"):
                amount = 0

            if not f.get("min-amount"):
                min_amount = 0


            # Update
            db.execute("UPDATE items SET item_category_id = ?, item_name = ?, manifacturer = ?, color = ?, unit_price = ?, unit_weight = ?, wt_unit = ?, length = ?, width = ?, height = ?, length_unit = ?, storage_place = ?, amount = ?, min_amount = ?, note1 = ?, note2 = ?, note3 = ? WHERE item_id = ?",
                       item_category_id, item_name, manifacturer, color, unit_price, unit_weight, wt_unit, length, width, height, length_unit, storage_place, amount, min_amount, note1, note2, note3, item_id)

            inv = db.execute("SELECT * FROM items JOIN categories ON item_category_id = category_id WHERE inventory_id = ?", int(p_inv[0]["id"]))

            session["inv"] = inv

            flash("Changes saved successfuly", "alert-success")
            return redirect("/edit-item")

    else:
        # Ensure user has permission
        if item_id not in [i['item_id'] for i in inv]:
            flash("permission denied!", "alert-danger")
            return redirect("/edit-item")


        for i in range(len(inv)):
            if inv[i]["item_id"] == item_id:
                item_data = inv[i]
                return render_template("edit_item.html", invs=invs, cats=cats, p_inv=p_inv, data=item_data)


@app.route("/edit-category/<int:category_id>", methods=["GET", "POST"])
@login_required
def edit_category(category_id):

    user_id = session["user_id"]
    invs = session["invs"]
    p_inv = session["p_inv"]
    cats = session["cats"]

    if request.method == "POST":
        f = request.form

        # Ensure role name at least submitted
        if not f.get("category-name").strip():
            flash("Category name is missing", "alert-danger")

        # Ensure user have permission
        elif category_id not in [i["category_id"] for i in cats]:
            flash("Permission denied!", "alert-danger")

        else:
            # Submitted data
            inventory_id = f.get("inventory")
            category_name = f.get("category-name")
            about_items = f.get("about-items")

            # Insert submitted data into the database
            db.execute("UPDATE categories SET inventory_id = ?, category_name = ?, about_items = ? WHERE category_id = ?",
                       inventory_id, category_name, about_items, category_id)

            # Update session data
            u_cats = db.execute ("SELECT * FROM admins WHERE admin_id = ? AND admin_role in ('Admin', 'Editor')", user_id)

            ids = []

            for i in range(len(u_cats)):
                ids.append(u_cats[i]['inventory_id'])

            if len(ids) <= 1:
                if len(ids) == 0:
                    ids = 0
                else:
                    ids = ids[0]
                cats = db.execute("SELECT * FROM categories WHERE inventory_id = ?", ids)

            else:
                ids = tuple(ids)
                cats = db.execute(f"SELECT * FROM categories WHERE inventory_id IN {ids}")

            inv = db.execute("SELECT * FROM items JOIN categories ON item_category_id = category_id WHERE inventory_id = ?", int(p_inv[0]["id"]))

            session["cats"] = cats
            session["inv"] = inv

            flash("Changes saved", "alert-success")

            return redirect("/edit-category")

    else:
        # Ensure user have permission
        if category_id not in [i["category_id"] for i in cats]:
            flash("Permission denied!", "alert-danger")
            return redirect("/edit-category")
        else:
            for i in range(len(cats)):
                if cats[i]["category_id"] == category_id:
                    category_data = cats[i]
                    break

            return render_template("edit_category.html", invs=invs, p_inv=p_inv, data=category_data)


@app.route("/edit-inventory/<int:inventory_id>", methods=["GET", "POST"])
@login_required
def edit_inventory(inventory_id):

    invs = session['invs']
    p_inv = session["p_inv"]

    if inventory_id not in [i['id'] for i in invs]:
        flash("Permission denied!", "alert-danger")
        return redirect("/edit-inventory")

    if request.method == "POST":

        inventories = []
        invs = session['invs']
        for inv in invs:
            if inv['id'] != inventory_id:
                inventories.append(inv["name"])

        f = request.form
        if not f.get("inventory-name").strip():
            flash("Inventory name is missing!", "alert-danger")
            return redirect("/edit-inventory")

        elif f.get("inventory-name").strip() in inventories:
                flash("One of your inventories has the same name", "alert-danger")
                return redirect("/add-inventory")
        else:
            user_id = session["user_id"]
            inventory_name = f.get("inventory-name")
            inventory_address = f.get("inventory-address")
            inventory_currency = f.get("inventory-currency")
            if not inventory_currency:
                inventory_currency = "EGP"

            db.execute("Update inventories SET inventory_name = ?, inventory_address = ?,  inventory_currency = ? WHERE inventory_id = ?",
                        inventory_name, inventory_address, inventory_currency, inventory_id)

            # make primary
            db.execute("UPDATE users SET primary_inventory = ? WHERE user_id = ?",
                        inventory_id, user_id)

            return redirect("/")

    else:

        for i in range(len(invs)):
            if invs[i]['id'] == inventory_id:
                inventory_data = invs[i]
                break

        return render_template("edit_inventory.html", invs=invs, p_inv=p_inv, data=inventory_data, inv_id=inventory_id)


@app.route("/remove-item", methods=["GET", "POST"])
@login_required
def remove_item():
    invs = session["invs"]
    p_inv = session["p_inv"]
    inv = session['inv']
    cats = session['cats']

    if request.method == "POST":
        item_id = int(request.form.get('item-id'))
        if item_id in [i["item_id"] for i in inv]:
            db.execute("DELETE FROM ITEMS WHERE item_id = ?", item_id)
            inv = db.execute("SELECT * FROM items JOIN categories ON item_category_id = category_id WHERE inventory_id = ?", p_inv[0]['id'])
            session['inv'] = inv
            flash("Item removed seccessfully", "alert-success")
        else:
            flash("Item doesn't belong to current inventory", "alert-danger")
        return redirect("/remove-item")
    else:
        return render_template("remove_item.html", invs=invs, n=len(invs), p_inv=p_inv, cats=cats, inv=inv)


@app.route("/remove-category/", methods=["GET", "POST"])
@login_required
def remove_category():
    user_id = session["user_id"]
    invs = session["invs"]
    cats = session["cats"]
    p_inv = session["p_inv"]

    if request.method == "POST":
        if not request.form.get("item-category"):
            flash("Please select category first", "alert-danger")
        elif int(request.form.get("item-category")) not in [i["category_id"] for i in cats]:
            flash("Permission denied!", "alert-danger")
        else:
            category_id = request.form.get("item-category")
            db.execute("DELETE FROM items WHERE item_category_id = ?", category_id)
            db.execute("DELETE FROM categories WHERE category_id = ?", category_id)

            inv = db.execute("SELECT * FROM items JOIN categories ON item_category_id = category_id WHERE inventory_id = ?", p_inv[0]['id'])
            session["inv"] = inv

            u_cats = db.execute ("SELECT * FROM admins WHERE admin_id = ? AND admin_role in ('Admin', 'Editor')", user_id)

            ids = []
            for i in range(len(u_cats)):
                ids.append(u_cats[i]['inventory_id'])

            if len(ids) <= 1:
                if len(ids) == 0:
                    ids = 0
                else:
                    ids = ids[0]
                cats = db.execute("SELECT * FROM categories WHERE inventory_id = ?", ids)

            else:
                ids = tuple(ids)
                cats = db.execute(f"SELECT * FROM categories WHERE inventory_id IN {ids}")

            session["cats"] = cats
            flash("Category removed successfully", "alert-success")

        return redirect("/remove-category")

    else:
        return render_template("remove_category.html", invs=invs, n=len(invs), p_inv=p_inv, cats=cats)


@app.route("/remove-inventory", methods=["GET", "POST"])
@login_required
def remove_inventory():

    # session data
    user_id = session["user_id"]
    invs = session["invs"]
    cats = session["cats"]
    p_inv = session["p_inv"]

    if request.method == "POST":
        # Ensure if inventory id is submitted
        if not request.form.get("inventory"):
            flash("Please select inventory first", "alert-danger")

        # Ensure that inventory belong to the user inventories
        elif int(request.form.get("inventory")) not in [i["id"] for i in invs]:
            flash("Permission denied!", "alert-danger")

        # Ensure there is at least two inventories before make deletion
        elif len([i["id"] for i in invs]) < 2:
            flash("You can't remove all inventories!", "alert-danger")

        # Delete inventory, included categories and included items
        else:

            # get inventory id
            inventory_id = request.form.get("inventory")

            # get included categories ids
            categories = db.execute("SELECT category_id FROM categories WHERE inventory_id = ?", inventory_id)
            category_id = [i["category_id"] for i in categories]

            if len(category_id) <= 1:
                if len(category_id) == 0:
                    category_id = 0
                else:
                    category_id = category_id[0]
                db.execute("DELETE FROM items WHERE item_category_id = ?", category_id)
                db.execute("DELETE FROM categories WHERE category_id = ?", category_id)

            else:
                category_id = tuple(category_id)
                db.execute(f"DELETE FROM items WHERE item_category_id IN {category_id}")
                db.execute(f"DELETE FROM categories WHERE category_id IN {category_id}")

            db.execute("DELETE FROM admins WHERE inventory_id = ?", inventory_id)
            db.execute("DELETE FROM inventories WHERE inventory_id = ?", inventory_id)

            # if deleted inventory is the current change it
            if int(request.form.get("inventory")) == p_inv[0]["id"]:
                for i in invs:
                    if i["id"] != p_inv[0]["id"]:
                        db.execute("UPDATE users SET primary_inventory = ? WHERE user_id = ?", i["id"], user_id)
                        break

            # refresh user index
            user_invs = db.execute("SELECT * FROM inventories JOIN admins ON inventories.inventory_id = admins.inventory_id WHERE admin_id = ?", user_id)

            p_inv_id = db.execute("SELECT * FROM users WHERE user_id = ?", user_id)[0]["primary_inventory"]
            inv = db.execute("SELECT * FROM items JOIN categories ON item_category_id = category_id WHERE inventory_id = ?", p_inv_id)

            invs = []
            p_inv = {}
            p_inv_value = 0

            for i in range(len(inv)):
                p_inv_value += int(inv[i]['amount']) * int(inv[i]['unit_price'])

            for i in range(len(user_invs)):
                if user_invs[i]["inventory_id"] == p_inv_id:
                    active = "active"
                    p_inv = [{"id": user_invs[i]["inventory_id"], "name": user_invs[i]["inventory_name"], "address": user_invs[i]["inventory_address"], "currency": user_invs[i]["inventory_currency"], "value": p_inv_value}]
                else:
                    active = ""

                invs.append({"id": user_invs[i]["inventory_id"], "name": user_invs[i]["inventory_name"], "active": active})


            # User categories
            u_cats = db.execute ("SELECT * FROM admins WHERE admin_id = ? AND admin_role in ('Admin', 'Editor')", user_id)

            ids = []
            for i in range(len(u_cats)):
                ids.append(u_cats[i]['inventory_id'])

            if len(ids) <= 1:
                if len(ids) == 0:
                    ids = 0
                else:
                    ids = ids[0]
                cats = db.execute("SELECT * FROM categories WHERE inventory_id = ?", ids)

            else:
                ids = tuple(ids)
                cats = db.execute(f"SELECT * FROM categories WHERE inventory_id IN {ids}")

            # Set to use later
            session["invs"] = invs
            session["p_inv"] = p_inv
            session["inv"] = inv
            session["cats"] = cats

            # Flash success message
            flash("inventory removed successfully", "alert-success")

        return redirect("/remove-inventory")
    else:
        return render_template("remove_inventory.html", invs=invs, n=len(invs), p_inv=p_inv)


""" Sign up """
@app.route("/sign-up", methods=["GET", "POST"])
def sign_up():

    # User reached route via POST
    if request.method == "POST":

        first_name = request.form.get("first-name")
        last_name = request.form.get("last-name")
        email = request.form.get("email")
        password = request.form.get("password")
        password_conf = request.form.get("password-conf")
        user_data = db.execute("SELECT * FROM users WHERE email = :email;", email=email)
        inventory_name = request.form.get("inventory-name")
        inventory_address = request.form.get("inventory-address")

        policy = PasswordPolicy.from_names(
            length=8,  # min length : 8 chars
            uppercase=1,  # need min. 0 uppercase letters
            numbers=1,  # need min. 1 digits
            special=1,  # need min. 1 special characters
            nonletters=0,  # need min. 2 non-letter characters (digits, specials, anything)
        )

        # Ensure first name was submitted
        if not request.form.get("first-name"):
            return apology("must provide first name", 403)

        # Ensure last name was submitted
        elif not request.form.get("last-name"):
            return apology("must provide last name", 403)

        # Ensure company name was submitted
        elif not request.form.get("inventory-name"):
            return apology("must provide inventory name", 403)

        # Ensure email is not already in use
        elif len(user_data) == 1:
            return apology("email already signed up", 403)

        # Ensure password was submitted
        elif not password:
            return apology("must provide password", 403)

        # Ensure password confirmation was submitted
        elif not password_conf:
            return apology("must confirm your password", 403)

        # Ensure password confimation matches password
        elif password != password_conf:
            return apology("Passwords doesn't match", 403)

        # Ensure password is strong
        elif len(policy.test(password)) != 0:
            return apology("password is not strong enough", 403)

        # hash the password
        hash = generate_password_hash(password)

        # Insert username and password hash into users
        db.execute("INSERT INTO users (first_name, last_name, email, hash) VALUES (?, ?, ?, ?);",
                   first_name, last_name, email, hash)

        # Query database for username
        user_data = db.execute("SELECT * FROM users WHERE email = ?;", email)

        # Remember which user has logged in (login with registered username and password)
        session["user_id"] = user_data[0]["user_id"]
        user_id = session["user_id"]
        session['logged_in'] = True

        # Insert inventory holding company name
        db.execute("INSERT INTO inventories (inventory_creator_id, inventory_name, inventory_address, inventory_currency) VALUES (?, ?, ?, ?);",
                   user_id, inventory_name, inventory_address, "USD")

        # Set created inventory as primary
        inv_id = db.execute("SELECT inventory_id FROM inventories WHERE inventory_creator_id = ?", user_id)[0]["inventory_id"]
        db.execute("UPDATE users SET primary_inventory = ? WHERE user_id = ?", inv_id, user_id)


        # Assign user as admin
        db.execute("INSERT INTO admins (inventory_id, admin_id, admin_role) VALUES (?, ?, ?)",
                    inv_id, user_id, "Admin")

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        session['logged_in'] = False
        return render_template("sign_up.html")


""" Sign in """
@app.route("/sign-in", methods=["GET", "POST"])
def sign_in():


    # Forget any user_id
    session.clear()
    session['logged_in'] = False

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("email"):
            return apology("must provide email", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        user_data = db.execute("SELECT * FROM users WHERE email = ?;", request.form.get("email"))

        # Ensure username exists and password is correct
        if len(user_data) != 1 or not check_password_hash(user_data[0]["hash"], request.form.get("password")):
            return apology("invalid email and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = user_data[0]["user_id"]
        session['logged_in'] = True

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        session['logged_in'] = False
        return render_template("sign_in.html")


""" Sign out """
@app.route("/sign-out")
def sign_out():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


""" Error handling"""
def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)