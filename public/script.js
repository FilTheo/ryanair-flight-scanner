document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('flight-search-form');
    const resultsContainer = document.getElementById('flight-results-container');
    const loadingIndicator = document.getElementById('loading-indicator');
    const errorMessageDiv = document.getElementById('error-message');

    // Set minimum date to today
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('departureDate').min = today;

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        loadingIndicator.style.display = 'block';
        resultsContainer.innerHTML = '';
        errorMessageDiv.style.display = 'none';
        errorMessageDiv.textContent = '';
        document.getElementById('results-info').style.display = 'none';

        const formData = new FormData(form);

        // Build the request payload to match the backend FlightSearchRequest model
        // Always one-way, so return_date is null and return flexibility is 0
        const requestPayload = {
            origin: formData.get('origin').toUpperCase(),
            destination: formData.get('destination').toUpperCase(),
            departure_date: formData.get('departureDate'),
            return_date: null, // Always one-way
            passengers: {
                adults: 1,
                teens: 0,
                children: 0,
                infants: 0
            },
            date_flexibility: {
                departure: parseInt(formData.get('dateFlexibilityDeparture')),
                return_date: 0 // Always one-way
            },
            max_connections: parseInt(formData.get('maxConnections')),
            currency: formData.get('currency').toUpperCase() || 'EUR',
            include_connections: parseInt(formData.get('maxConnections')) > 0
        };

        try {
            console.log('Sending request:', JSON.stringify(requestPayload, null, 2));

            const response = await fetch('/api/flights/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(requestPayload)
            });

            loadingIndicator.style.display = 'none';

            if (!response.ok) {
                let errorData;
                try {
                    errorData = await response.json();
                } catch (e) {
                    errorData = { detail: `HTTP error! status: ${response.status}` };
                }
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Received response:', data);
            displayFlightResults(data);

        } catch (error) {
            loadingIndicator.style.display = 'none';
            showError(`Failed to fetch flights: ${error.message}`);
            console.error('Error fetching flights:', error);
        }
    });

    function showError(message) {
        errorMessageDiv.textContent = message;
        errorMessageDiv.style.display = 'block';
        loadingIndicator.style.display = 'none';
    }

    function displayFlightResults(data) {
        // Handle the actual backend response structure
        let flightOptions = data.flight_options || [];
        const resultsInfo = document.getElementById('results-info');

        if (!flightOptions || flightOptions.length === 0) {
            resultsContainer.innerHTML = '<div class="no-results">No flights found matching your criteria.</div>';
            resultsInfo.style.display = 'none';
            return;
        }

        // Sort flight options by price (cheapest first)
        flightOptions.sort((a, b) => (a.total_price || 0) - (b.total_price || 0));

        // Show the results info
        resultsInfo.style.display = 'block';

        flightOptions.forEach(option => {
            const optionDiv = document.createElement('div');
            optionDiv.className = 'flight-option';

            let legsHTML = '';
            if (option.legs && option.legs.length > 0) {
                option.legs.forEach((leg, index) => {
                    // Format individual leg price
                    const legPrice = leg.price !== undefined && leg.price !== null ? leg.price : 0;
                    const legCurrency = leg.currency || option.currency || 'EUR';
                    const priceDisplay = option.legs.length > 1 ?
                        `<p class="leg-price"><strong>Price:</strong> ${legPrice.toFixed(2)} ${legCurrency}</p>` : '';

                    legsHTML += `
                        <div class="flight-leg">
                            <h4>Leg ${index + 1}: ${leg.origin_airport} to ${leg.destination_airport}</h4>
                            <p><strong>Flight:</strong> ${leg.operator} ${leg.flight_number}</p>
                            <p><strong>Departure:</strong> ${formatDateTime(leg.departure_datetime)}</p>
                            <p><strong>Arrival:</strong> ${formatDateTime(leg.arrival_datetime)}</p>
                            <p><strong>Duration:</strong> ${formatDuration(leg.duration_minutes)}</p>
                            ${priceDisplay}
                        </div>
                    `;
                });
            }

            let layoversHTML = '';
            if (option.layovers && option.layovers.length > 0) {
                option.layovers.forEach(layover => {
                    layoversHTML += `
                        <div class="layover-info">
                            <p><strong>Layover at:</strong> ${layover.airport}</p>
                            <p><strong>Duration:</strong> ${formatDuration(layover.duration_minutes)}</p>
                        </div>
                    `;
                });
            }

            // Handle price display - use total_price and currency from the option
            const priceValue = option.total_price !== undefined ? option.total_price.toFixed(2) : 'N/A';
            const currencyCode = option.currency || 'EUR';

            optionDiv.innerHTML = `
                <h3>${option.type === 'one-stop' ? 'One-Stop Connection' : 'Direct Flight'}</h3>
                <p class="price">Total Price: ${priceValue} ${currencyCode}</p>
                ${legsHTML}
                ${layoversHTML}
            `;
            resultsContainer.appendChild(optionDiv);
        });
    }

    function formatDuration(totalMinutes) {
        if (totalMinutes === null || totalMinutes === undefined || totalMinutes < 0) {
            return 'N/A';
        }
        if (totalMinutes === 0) {
            return '0 minutes';
        }

        const hours = Math.floor(totalMinutes / 60);
        const minutes = totalMinutes % 60;

        let durationString = '';
        if (hours > 0) {
            durationString += `${hours} hour${hours > 1 ? 's' : ''}`;
        }
        if (minutes > 0) {
            if (hours > 0) {
                durationString += ' ';
            }
            durationString += `${minutes} minute${minutes > 1 ? 's' : ''}`;
        }
        return durationString;
    }

    function formatDateTime(dateTimeString) {
        try {
            const date = new Date(dateTimeString);
            return date.toLocaleString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                hour12: false
            });
        } catch (e) {
            return dateTimeString; // Return original if parsing fails
        }
    }

    // Add input validation and formatting
    document.getElementById('origin').addEventListener('input', function (e) {
        e.target.value = e.target.value.toUpperCase();
    });

    document.getElementById('destination').addEventListener('input', function (e) {
        e.target.value = e.target.value.toUpperCase();
    });

    document.getElementById('currency').addEventListener('input', function (e) {
        e.target.value = e.target.value.toUpperCase();
    });

    // IATA Lookup Functionality
    const iataLookupForm = document.getElementById('iata-lookup-form');
    const iataResultsContainer = document.getElementById('iata-results-container');
    const iataLoadingIndicator = document.getElementById('iata-loading-indicator');
    const iataErrorMessageDiv = document.getElementById('iata-error-message');
    const iataKnownCodeMessage = document.getElementById('iata-known-code-message');

    if (iataLookupForm) {
        iataLookupForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            iataLoadingIndicator.style.display = 'block';
            iataResultsContainer.innerHTML = '';
            iataErrorMessageDiv.style.display = 'none';
            iataErrorMessageDiv.textContent = '';
            iataKnownCodeMessage.style.display = 'none';

            const cityName = document.getElementById('city-name').value.trim();

            if (!cityName) {
                showIataError("Please enter a city name.");
                return;
            }

            try {
                const response = await fetch(`/api/airports/iata-lookup/${encodeURIComponent(cityName)}`, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json'
                    }
                });

                iataLoadingIndicator.style.display = 'none';

                if (!response.ok) {
                    let errorData;
                    try {
                        errorData = await response.json();
                    } catch (e) {
                        errorData = { detail: `HTTP error! status: ${response.status}` };
                    }
                    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                displayIataResults(data);

            } catch (error) {
                iataLoadingIndicator.style.display = 'none';
                showIataError(`Failed to fetch IATA codes: ${error.message}`);
                console.error('Error fetching IATA codes:', error);
            }
        });
    }

    function showIataError(message) {
        iataErrorMessageDiv.textContent = message;
        iataErrorMessageDiv.style.display = 'block';
        iataLoadingIndicator.style.display = 'none';
    }

    function displayIataResults(airports) {
        if (!airports || airports.length === 0) {
            iataResultsContainer.innerHTML = '<div class="no-results">No airports found for the specified city.</div>';
            iataKnownCodeMessage.style.display = 'none';
            return;
        }

        const ul = document.createElement('ul');
        ul.className = 'iata-results-list';

        airports.forEach(airport => {
            const li = document.createElement('li');
            li.textContent = `${airport.name} (${airport.iata_code}) - ${airport.city_name}, ${airport.country_name}`;
            ul.appendChild(li);
        });
        iataResultsContainer.appendChild(ul);
        iataKnownCodeMessage.style.display = 'block';
    }
}); 