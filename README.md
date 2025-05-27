# Ryanair Flight Scanner

A web application for finding cheap Ryanair flights with connection analysis, deployed on Vercel using Python serverless functions.

## Features

- **Flight Search**: Search for one-way and round-trip flights
- **Connection Analysis**: Find flights with up to one connection
- **Flexible Dates**: Search with date flexibility (+/- days)
- **Multiple Passengers**: Support for adults, teens, children, and infants
- **ANY Destination**: Search for flights to any destination from an origin
- **Responsive Design**: Works on desktop and mobile devices

## Technology Stack

- **Backend**: Python 3.12 (Vercel serverless functions)
- **Frontend**: HTML, CSS, JavaScript (vanilla)
- **Deployment**: Vercel
- **APIs**: Internal Ryanair API client (serverless-friendly)

## Project Structure

```
├── api/                    # Serverless API functions
│   ├── flights.py         # Flight search endpoint
│   ├── airports.py        # Airport data endpoint
│   └── health.py          # Health check endpoint
├── lib/                   # Core Python modules
│   ├── ryanair_client.py  # Ryanair API client
│   ├── flight_analyzer.py # Flight analysis logic
│   ├── models.py          # Data models
│   └── config.py          # Configuration
├── static/                # Frontend files
│   ├── index.html         # Main web interface
│   ├── style.css          # Styling
│   └── script.js          # Client-side logic
├── vercel.json            # Vercel deployment config
└── requirements.txt       # Python dependencies
```

## Setup

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ryanair-flight-scanner
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run locally** (choose one option):

   **Option A - Simple FastAPI server (recommended):**
   ```bash
   python simple_test_server.py
   ```
   Then open `http://localhost:8000` in your browser

   **Option B - Flask-based test server:**
   ```bash
   python local_test_server.py
   ```
   Then open `http://localhost:5001` in your browser

   **Option C - Run with Vercel CLI:**
   ```bash
   npm install -g vercel
   vercel dev
   ```
   Then open `http://localhost:3000` in your browser

### Deployment

1. **Deploy to Vercel**
   ```bash
   vercel --prod
   ```

## Usage

### Web Interface

1. **Open the application** in your web browser
2. **Select trip type**: One-way or Round-trip
3. **Enter flight details**:
   - Origin airport (3-letter IATA code, e.g., DUB)
   - Destination airport (3-letter IATA code or "ANY")
   - Departure date (and return date for round-trip)
   - Number of passengers by type
   - Date flexibility (optional)
   - Maximum connections (Direct or One-stop)
   - Currency (default: EUR)
4. **Click "Search Flights"** to find available options
5. **View results** with flight details, prices, and layover information

### API Endpoints

#### Search Flights
```
POST /api/flights/search
```

**Request Body:**
```json
{
  "origin": "DUB",
  "destination": "STN",
  "departure_date": "2024-12-20",
  "return_date": null,
  "passengers": {
    "adults": 1,
    "teens": 0,
    "children": 0,
    "infants": 0
  },
  "date_flexibility": {
    "departure": 0,
    "return_date": 0
  },
  "max_connections": 1,
  "currency": "EUR",
  "include_connections": true
}
```

**Response:**
```json
{
  "flight_options": [
    {
      "type": "direct",
      "total_price": 29.99,
      "currency": "EUR",
      "legs": [
        {
          "leg_type": "outbound",
          "origin_airport": "DUB",
          "destination_airport": "STN",
          "departure_datetime": "2024-12-20T06:00:00",
          "arrival_datetime": "2024-12-20T07:25:00",
          "flight_number": "FR123",
          "operator": "Ryanair",
          "duration_minutes": 85
        }
      ],
      "layovers": []
    }
  ]
}
```

#### Get Airports
```
GET /api/airports
```

#### Get Destinations from Origin
```
GET /api/airports/{origin_code}/destinations
```

## Use Cases

### 1. Direct Flight Search
Search for direct flights from Dublin to London Stansted:
- Origin: DUB
- Destination: STN
- Max Connections: Direct

### 2. Connection Flight Search
Find flights with one connection from Dublin to Barcelona:
- Origin: DUB
- Destination: BCN
- Max Connections: One-stop

### 3. Flexible Date Search
Search with date flexibility for better prices:
- Departure Date Flexibility: ±3 days
- Return Date Flexibility: ±2 days

### 4. ANY Destination Search
Discover all destinations from Dublin:
- Origin: DUB
- Destination: ANY

### 5. Round-trip Search
Book return flights:
- Trip Type: Round-trip
- Include return date and flexibility

## Configuration

Key configuration options in `lib/config.py`:

- `RYANAIR_API_URL`: Base URL for Ryanair API
- `TIMEOUT`: Request timeout in seconds
- `RETRIES`: Number of retry attempts
- `CACHE_TTL`: Cache time-to-live in seconds
- `MIN_LAYOVER_MINUTES`: Minimum layover time for connections
- `MAX_LAYOVER_MINUTES`: Maximum layover time for connections

## Error Handling

The application includes comprehensive error handling:

- **Input Validation**: Client-side and server-side validation
- **API Failures**: Graceful degradation with user-friendly messages
- **Rate Limiting**: Built-in retry logic with exponential backoff
- **Caching**: Reduces API calls and improves performance

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is for educational purposes. Please respect Ryanair's terms of service when using their data. 