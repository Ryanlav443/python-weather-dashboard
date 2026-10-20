
import requests
import pandas as pd
import plotly.express as px
import streamlit as st

# API URLs
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# Weather codes and their descriptions
WEATHER_CODES = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Fog", "🌫️"),
    48: ("Rime fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Moderate drizzle", "🌦️"),
    55: ("Heavy drizzle", "🌧️"),
    61: ("Slight rain", "🌧️"),
    63: ("Moderate rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    71: ("Slight snow", "🌨️"),
    73: ("Moderate snow", "🌨️"),
    75: ("Heavy snow", "❄️"),
    80: ("Rain showers", "🌦️"),
    81: ("Moderate rain showers", "🌧️"),
    82: ("Heavy rain showers", "⛈️"),
    85: ("Snow showers", "🌨️"),
    86: ("Heavy snow showers", "❄️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm with hail", "⛈️"),
    99: ("Severe thunderstorm with hail", "⛈️")
}


def weather_label(code):
    """Return the weather description and emoji."""
    return WEATHER_CODES.get(
        code, ("Unknown conditions", "🌡️")
    )


@st.cache_data(ttl=900)
def find_city(city_name):
    """Find a city's coordinates using the geocoding API."""
    response = requests.get(
        GEOCODING_URL,
        params={
            "name": city_name,
            "count": 1,
            "language": "en",
            "format": "json"
        },
        timeout=10
    )

    response.raise_for_status()
    results = response.json().get("results", [])

    if results:
        return results[0]

    return None


@st.cache_data(ttl=900)
def get_forecast(latitude, longitude):
    """Retrieve current weather and a seven-day forecast."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "apparent_temperature,"
            "precipitation,"
            "weather_code,"
            "wind_speed_10m"
        ),
        "daily": (
            "weather_code,"
            "temperature_2m_max,"
            "temperature_2m_min,"
            "precipitation_probability_max"
        ),
        "timezone": "auto",
        "forecast_days": 7
    }

    response = requests.get(
        FORECAST_URL,
        params=params,
        timeout=10
    )

    response.raise_for_status()
    return response.json()


# Configure the Streamlit page
st.set_page_config(
    page_title="Weather Dashboard",
    page_icon="🌦️",
    layout="wide"
)

# Page heading
st.title("🌦️ Weather Dashboard")
st.write(
    "Search for a city to view current weather "
    "conditions and the seven-day forecast."
)

# City search form
with st.form("weather_search"):
    city_name = st.text_input(
        "Enter a city name",
        placeholder="e.g. London, Belfast or Paris"
    )

    search_button = st.form_submit_button(
        "Get Weather",
        type="primary"
    )


# Process the search
if search_button:
    if not city_name.strip():
        st.warning("Please enter a city name.")

    else:
        try:
            with st.spinner("Loading weather data..."):
                city = find_city(city_name.strip())

                if city is None:
                    st.session_state.pop("weather_city", None)
                    st.session_state.pop("weather_data", None)
                    st.error(
                        "City not found. Check the spelling "
                        "and try again."
                    )

                else:
                    weather_data = get_forecast(
                        city["latitude"],
                        city["longitude"]
                    )

                    st.session_state["weather_city"] = city
                    st.session_state["weather_data"] = weather_data

        except requests.exceptions.Timeout:
            st.error(
                "The request timed out. Please try again."
            )

        except requests.exceptions.RequestException:
            st.error(
                "Unable to connect to the weather service. "
                "Check your internet connection."
            )

        except (KeyError, ValueError):
            st.error(
                "The weather data could not be processed."
            )


# Display results saved in the session
city = st.session_state.get("weather_city")
weather_data = st.session_state.get("weather_data")


if city and weather_data:

    current = weather_data["current"]

    description, emoji = weather_label(
        current["weather_code"]
    )

    # Display the location
    location_parts = [
        city.get("name"),
        city.get("admin1"),
        city.get("country")
    ]

    location = ", ".join(
        dict.fromkeys(
            part for part in location_parts if part
        )
    )

    st.subheader(f"{emoji} {location}")

    st.caption(
        f"Local time: {current.get('time', 'Unavailable')}"
    )

    # Current weather metrics
    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Temperature",
        f"{current['temperature_2m']:.1f} °C"
    )

    col2.metric(
        "Feels Like",
        f"{current['apparent_temperature']:.1f} °C"
    )

    col3.metric(
        "Humidity",
        f"{current['relative_humidity_2m']}%"
    )

    col4.metric(
        "Wind Speed",
        f"{current['wind_speed_10m']:.1f} km/h"
    )

    st.info(
        f"Current conditions: {description} | "
        f"Precipitation: {current['precipitation']} mm"
    )

    # Prepare the forecast data
    daily = weather_data["daily"]

    forecast_df = pd.DataFrame({
        "Date": pd.to_datetime(daily["time"]),
        "High (°C)": daily["temperature_2m_max"],
        "Low (°C)": daily["temperature_2m_min"],
        "Rain Chance (%)": (
            daily["precipitation_probability_max"]
        ),
        "Weather Code": daily["weather_code"]
    })

    forecast_df["Day"] = forecast_df["Date"].dt.strftime(
        "%a, %d %b"
    )

    forecast_df["Conditions"] = forecast_df[
        "Weather Code"
    ].apply(
        lambda code: (
            f"{weather_label(int(code))[1]} "
            f"{weather_label(int(code))[0]}"
        )
    )

    # Display the temperature chart
    st.subheader("📈 Seven-Day Temperature Forecast")

    chart_df = forecast_df.melt(
        id_vars=["Day"],
        value_vars=["High (°C)", "Low (°C)"],
        var_name="Temperature",
        value_name="Degrees Celsius"
    )

    fig = px.line(
        chart_df,
        x="Day",
        y="Degrees Celsius",
        color="Temperature",
        markers=True,
        title="Daily High and Low Temperatures"
    )

    fig.update_layout(
        hovermode="x unified",
        legend_title_text=""
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # Display the forecast table
    st.subheader("📅 Daily Forecast")

    display_df = forecast_df[
        [
            "Day",
            "Conditions",
            "High (°C)",
            "Low (°C)",
            "Rain Chance (%)"
        ]
    ].copy()

    display_df["High (°C)"] = display_df[
        "High (°C)"
    ].map(lambda value: f"{value:.1f}")

    display_df["Low (°C)"] = display_df[
        "Low (°C)"
    ].map(lambda value: f"{value:.1f}")

    display_df["Rain Chance (%)"] = display_df[
        "Rain Chance (%)"
    ].apply(
        lambda value: (
            "N/A" if pd.isna(value)
            else f"{int(value)}%"
        )
    )

    st.dataframe(
        display_df,
        hide_index=True,
        use_container_width=True
    )

    st.caption(
        "Weather data provided by Open-Meteo. "
        "Forecasts are estimates and may change."
    )

else:
    st.markdown(
        """
        ### Welcome!

        Enter a city above to see its weather.

        **Dashboard features:**
        - Current weather conditions
        - Temperature, humidity and wind speed
        - Seven-day weather forecast
        - Interactive temperature chart
        - Daily forecast table
        """
    )