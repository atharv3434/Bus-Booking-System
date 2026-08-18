import os
import sqlite3
import random
import string
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, g, jsonify

app = Flask(__name__)
app.secret_key = "super_secret_bus_booking_key_2026"
DATABASE = "bus_booking.db"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def generate_pnr():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def init_db():
    """Initializes the database schema and seeds initial bus route data."""
    with app.app_context():
        db = get_db()
        cursor = db.cursor()

        # Buses Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS buses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bus_number TEXT NOT NULL UNIQUE,
                operator_name TEXT NOT NULL,
                bus_type TEXT NOT NULL,
                source TEXT NOT NULL,
                destination TEXT NOT NULL,
                departure_time TEXT NOT NULL,
                arrival_time TEXT NOT NULL,
                total_seats INTEGER NOT NULL DEFAULT 32,
                fare REAL NOT NULL
            )
        """
        )

        # Bookings Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pnr TEXT UNIQUE NOT NULL,
                bus_id INTEGER NOT NULL,
                travel_date TEXT NOT NULL,
                passenger_name TEXT NOT NULL,
                passenger_email TEXT NOT NULL,
                passenger_phone TEXT NOT NULL,
                seats_booked TEXT NOT NULL,
                seat_count INTEGER NOT NULL,
                total_fare REAL NOT NULL,
                booking_timestamp TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'CONFIRMED',
                FOREIGN KEY (bus_id) REFERENCES buses(id)
            )
        """
        )

        # Seed sample buses if none exist
        cursor.execute("SELECT COUNT(*) as count FROM buses")
        if cursor.fetchone()["count"] == 0:
            sample_buses = [
                (
                    "MH-12-AB-1001",
                    "Eagle Express",
                    "AC Sleeper (2+1)",
                    "Pune",
                    "Bengaluru",
                    "18:30",
                    "08:00",
                    32,
                    1450.0,
                ),
                (
                    "MH-12-CD-2002",
                    "Royal Travels",
                    "Multi-Axle Volvo AC",
                    "Pune",
                    "Mumbai",
                    "06:00",
                    "09:30",
                    36,
                    450.0,
                ),
                (
                    "KA-01-EF-3003",
                    "Kaveri Transports",
                    "AC Semi-Sleeper",
                    "Bengaluru",
                    "Chennai",
                    "22:00",
                    "05:30",
                    32,
                    850.0,
                ),
                (
                    "DL-01-GH-4004",
                    "Northern Star",
                    "BharatBenz AC",
                    "Delhi",
                    "Jaipur",
                    "07:15",
                    "12:45",
                    32,
                    650.0,
                ),
                (
                    "MH-14-IJ-5005",
                    "Intercity Express",
                    "Volvo 9600 AC",
                    "Mumbai",
                    "Goa",
                    "20:00",
                    "07:30",
                    30,
                    1800.0,
                ),
                (
                    "KA-04-KL-6006",
                    "Silicon Shuttle",
                    "Electric AC Coach",
                    "Bengaluru",
                    "Hyderabad",
                    "21:30",
                    "06:30",
                    32,
                    1200.0,
                ),
            ]
            cursor.executemany(
                """
                INSERT INTO buses (bus_number, operator_name, bus_type, source, destination, departure_time, arrival_time, total_seats, fare)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                sample_buses,
            )
            db.commit()


@app.route("/")
def index():
    source = request.args.get("source", "").strip()
    destination = request.args.get("destination", "").strip()
    travel_date = request.args.get(
        "travel_date", date.today().strftime("%Y-%m-%d")
    )

    db = get_db()
    cursor = db.cursor()

    # Get distinct sources and destinations for dropdown autocomplete
    sources = [
        row["source"]
        for row in cursor.execute(
            "SELECT DISTINCT source FROM buses ORDER BY source"
        ).fetchall()
    ]
    destinations = [
        row["destination"]
        for row in cursor.execute(
            "SELECT DISTINCT destination FROM buses ORDER BY destination"
        ).fetchall()
    ]

    buses = []
    if source and destination:
        cursor.execute(
            """
            SELECT * FROM buses 
            WHERE LOWER(source) = LOWER(?) AND LOWER(destination) = LOWER(?)
        """,
            (source, destination),
        )
        bus_rows = cursor.fetchall()

        for b in bus_rows:
            # Calculate remaining seats for selected travel date
            cursor.execute(
                """
                SELECT seats_booked FROM bookings 
                WHERE bus_id = ? AND travel_date = ? AND status = 'CONFIRMED'
            """,
                (b["id"], travel_date),
            )
            booked_rows = cursor.fetchall()
            booked_seats_set = set()
            for r in booked_rows:
                booked_seats_set.update(r["seats_booked"].split(","))

            available_count = b["total_seats"] - len(booked_seats_set)
            bus_dict = dict(b)
            bus_dict["available_seats"] = max(0, available_count)
            buses.append(bus_dict)

    return render_template(
        "index.html",
        sources=sources,
        destinations=destinations,
        buses=buses,
        selected_source=source,
        selected_destination=destination,
        travel_date=travel_date,
    )


@app.route("/select-seats/<int:bus_id>")
def select_seats(bus_id):
    travel_date = request.args.get("travel_date")
    if not travel_date:
        flash("Please pick a valid travel date first.", "warning")
        return redirect(url_for("index"))

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM buses WHERE id = ?", (bus_id,))
    bus = cursor.fetchone()
    if not bus:
        flash("Selected bus not found.", "danger")
        return redirect(url_for("index"))

    # Fetch currently booked seats for this date
    cursor.execute(
        """
        SELECT seats_booked FROM bookings 
        WHERE bus_id = ? AND travel_date = ? AND status = 'CONFIRMED'
    """,
        (bus_id, travel_date),
    )
    bookings = cursor.fetchall()

    occupied_seats = set()
    for row in bookings:
        occupied_seats.update(row["seats_booked"].split(","))

    return render_template(
        "select_seats.html",
        bus=bus,
        travel_date=travel_date,
        occupied_seats=list(occupied_seats),
    )


@app.route("/confirm-booking", methods=["POST"])
def confirm_booking():
    bus_id = request.form.get("bus_id")
    travel_date = request.form.get("travel_date")
    selected_seats = request.form.get("selected_seats", "").strip()

    if not selected_seats:
        flash("Please select at least one seat to proceed.", "warning")
        return redirect(
            url_for("select_seats", bus_id=bus_id, travel_date=travel_date)
        )

    seats_list = [s.strip() for s in selected_seats.split(",") if s.strip()]

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM buses WHERE id = ?", (bus_id,))
    bus = cursor.fetchone()

    total_fare = len(seats_list) * bus["fare"]

    return render_template(
        "booking_confirm.html",
        bus=bus,
        travel_date=travel_date,
        selected_seats=seats_list,
        total_fare=total_fare,
    )


@app.route("/process-payment", methods=["POST"])
def process_payment():
    bus_id = request.form.get("bus_id")
    travel_date = request.form.get("travel_date")
    selected_seats = request.form.get("selected_seats")
    name = request.form.get("passenger_name", "").strip()
    email = request.form.get("passenger_email", "").strip()
    phone = request.form.get("passenger_phone", "").strip()

    if not (bus_id and travel_date and selected_seats and name and email and phone):
        flash("All fields are required to confirm booking.", "danger")
        return redirect(url_for("index"))

    seats_list = [s.strip() for s in selected_seats.split(",") if s.strip()]
    db = get_db()
    cursor = db.cursor()

    # Verify if any seat was taken concurrently
    cursor.execute(
        """
        SELECT seats_booked FROM bookings 
        WHERE bus_id = ? AND travel_date = ? AND status = 'CONFIRMED'
    """,
        (bus_id, travel_date),
    )
    existing_bookings = cursor.fetchall()
    taken_seats = set()
    for row in existing_bookings:
        taken_seats.update(row["seats_booked"].split(","))

    conflict = [seat for seat in seats_list if seat in taken_seats]
    if conflict:
        flash(
            f"Seat(s) {', '.join(conflict)} were just booked by another user. Please reselect.",
            "danger",
        )
        return redirect(
            url_for("select_seats", bus_id=bus_id, travel_date=travel_date)
        )

    # Fetch fare
    cursor.execute("SELECT fare FROM buses WHERE id = ?", (bus_id,))
    bus = cursor.fetchone()
    total_fare = len(seats_list) * bus["fare"]
    pnr = generate_pnr()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
        INSERT INTO bookings 
        (pnr, bus_id, travel_date, passenger_name, passenger_email, passenger_phone, seats_booked, seat_count, total_fare, booking_timestamp, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'CONFIRMED')
    """,
        (
            pnr,
            bus_id,
            travel_date,
            name,
            email,
            phone,
            ",".join(seats_list),
            len(seats_list),
            total_fare,
            now_str,
        ),
    )

    db.commit()
    return redirect(url_for("ticket", pnr=pnr))


@app.route("/ticket/<pnr>")
def ticket(pnr):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT b.*, bu.bus_number, bu.operator_name, bu.bus_type, bu.source, bu.destination, bu.departure_time, bu.arrival_time
        FROM bookings b
        JOIN buses bu ON b.bus_id = bu.id
        WHERE b.pnr = ?
    """,
        (pnr,),
    )
    booking = cursor.fetchone()
    if not booking:
        flash("Ticket not found with the provided PNR.", "danger")
        return redirect(url_for("index"))

    return render_template("ticket.html", booking=booking)


@app.route("/my-bookings", methods=["GET", "POST"])
def my_bookings():
    bookings = []
    search_query = ""
    if request.method == "POST":
        search_query = request.form.get("search_query", "").strip()
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT b.*, bu.bus_number, bu.operator_name, bu.source, bu.destination, bu.departure_time
            FROM bookings b
            JOIN buses bu ON b.bus_id = bu.id
            WHERE b.pnr = ? OR b.passenger_email = ? OR b.passenger_phone = ?
            ORDER BY b.id DESC
        """,
            (search_query.upper(), search_query, search_query),
        )
        bookings = cursor.fetchall()
        if not bookings:
            flash("No bookings found matching your search.", "info")

    return render_template(
        "my_bookings.html", bookings=bookings, search_query=search_query
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)