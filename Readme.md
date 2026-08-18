# SwiftBus - Online Bus Booking System

A lightweight, full-stack Bus Ticket Reservation platform developed using **Python (Flask)**, **SQLite**, and **Bootstrap 5**.

## Features
- **Route & Bus Search**: Filter by origin, destination, and travel date with auto-populated hubs.
- **Visual 2x2 Interactive Seat Picker**: Real-time status indication (Available, Selected, Occupied).
- **Seat Conflict Prevention**: Protects against concurrent double-booking of seats.
- **E-Ticket Generation**: Boarding pass with auto-generated unique PNR and printable format.
- **Ticket Lookup**: Search past and upcoming bookings via PNR, registered Email, or Mobile number.

## Getting Started

### 1. Prerequisites
- Python 3.9+ installed on your machine.

### 2. Setup Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate