import dash
from dash import dcc, html, Input, Output, dash_table
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import dash_bootstrap_components as dbc
import firebase_admin
from firebase_admin import credentials, db, firestore
from datetime import datetime
import os
import json
from geopy.distance import geodesic

# Initialize Firebase
def initialize_firebase():
    try:
        # Load Firebase credentials from environment variable
        firebase_json = os.getenv("FIREBASE_CREDENTIALS")

        if not firebase_json:
            raise ValueError("Firebase credentials not found in environment variables")

        cred_dict = json.loads(firebase_json)
        
        # Initialize Firebase app if not already initialized
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://smartaid-6c5c0-default-rtdb.firebaseio.com/'
            })
        return True
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        return False

# Initialize Firebase connection
firebase_initialized = initialize_firebase()

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
server = app.server

def fetch_firebase_data():
    """Fetch data from Firebase Realtime Database and Firestore"""
    try:
        if not firebase_initialized:
            return {
                'detections': pd.DataFrame(),
                'locations': pd.DataFrame(),
                'ultrasonic': pd.DataFrame(),
                'battery': pd.DataFrame(),
                'motion': pd.DataFrame(),
                'system_health': pd.DataFrame()
            }
        
        # Initialize Firestore client
        db_firestore = firestore.client()
        
        # Dictionary to hold all data
        data_dict = {
            'detections': pd.DataFrame(),
            'locations': pd.DataFrame(),
            'ultrasonic': pd.DataFrame(),
            'battery': pd.DataFrame(),
            'motion': pd.DataFrame(),
            'system_health': pd.DataFrame()
        }
        
        # Fetch detection data from Realtime Database
        ref = db.reference('/detections')
        detection_data = ref.get()
        if detection_data:
            records = []
            for timestamp, values in detection_data.items():
                record = values.copy()
                record['timestamp'] = datetime.fromtimestamp(float(timestamp))
                records.append(record)
            data_dict['detections'] = pd.DataFrame(records)
        
        # Fetch location data from Firestore
        loc_ref = db_firestore.collection('location_logs')
        loc_data = [doc.to_dict() for doc in loc_ref.stream()]
        if loc_data:
            data_dict['locations'] = pd.DataFrame(loc_data)
            # Calculate distance between points if we have enough data
            if len(data_dict['locations']) > 1:
                distances = [0]
                for i in range(1, len(data_dict['locations'])):
                    point1 = (data_dict['locations'].iloc[i-1]['latitude'], 
                             data_dict['locations'].iloc[i-1]['longitude'])
                    point2 = (data_dict['locations'].iloc[i]['latitude'], 
                             data_dict['locations'].iloc[i]['longitude'])
                    distances.append(geodesic(point1, point2).meters)
                data_dict['locations']['distance_meters'] = distances
        
        # Fetch ultrasonic sensor data from Firestore
        ultra_ref = db_firestore.collection('ultrasonic_logs')
        ultra_data = [doc.to_dict() for doc in ultra_ref.stream()]
        if ultra_data:
            data_dict['ultrasonic'] = pd.DataFrame(ultra_data)
        
        # Fetch battery data from Firestore
        battery_ref = db_firestore.collection('battery_logs')
        battery_data = [doc.to_dict() for doc in battery_ref.stream()]
        if battery_data:
            data_dict['battery'] = pd.DataFrame(battery_data)
        
        # Fetch motion status data from Firestore
        motion_ref = db_firestore.collection('motion_logs')
        motion_data = [doc.to_dict() for doc in motion_ref.stream()]
        if motion_data:
            data_dict['motion'] = pd.DataFrame(motion_data)
        
        # Fetch system health data from Firestore
        health_ref = db_firestore.collection('system_health_logs')
        health_data = [doc.to_dict() for doc in health_ref.stream()]
        if health_data:
            data_dict['system_health'] = pd.DataFrame(health_data)
        
        return data_dict
        
    except Exception as e:
        print(f"Error fetching Firebase data: {e}")
        return {
            'detections': pd.DataFrame(),
            'locations': pd.DataFrame(),
            'ultrasonic': pd.DataFrame(),
            'battery': pd.DataFrame(),
            'motion': pd.DataFrame(),
            'system_health': pd.DataFrame()
        }

# =============================================
# Dashboard Layout
# =============================================

app.layout = dbc.Container(fluid=True, children=[
    # Title
    dbc.Row([
        dbc.Col(html.H1("Smart Hat Analytics Dashboard", 
                       className="text-center my-4"))
    ]),
    
    # Refresh interval
    dcc.Interval(id='interval-component', interval=10*1000, n_intervals=0),
    
    # Connection status indicator
    dbc.Row([
        dbc.Col(html.Div(id='connection-status', className="text-center mb-3"))
    ]),
    
    # System Metrics Row
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("CPU Usage (%)", className="h5"),
            dbc.CardBody(dcc.Graph(id='cpu-graph'))
        ], className="shadow"), md=4),
        
        dbc.Col(dbc.Card([
            dbc.CardHeader("Memory Usage (%)", className="h5"),
            dbc.CardBody(dcc.Graph(id='mem-graph'))
        ], className="shadow"), md=4),
        
        dbc.Col(dbc.Card([
            dbc.CardHeader("Temperature (°C)", className="h5"),
            dbc.CardBody(dcc.Graph(id='temp-graph'))
        ], className="shadow"), md=4)
    ], className="mb-4"),
    
    # Location and Battery Row
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Location Tracking", className="h5"),
            dbc.CardBody(dcc.Graph(id='location-map'))
        ], className="shadow"), md=8),
        
        dbc.Col(dbc.Card([
            dbc.CardHeader("Battery Level", className="h5"),
            dbc.CardBody(dcc.Graph(id='battery-graph'))
        ], className="shadow"), md=4)
    ], className="mb-4"),
    
    # Detection Metrics Row
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Detection Frequency", className="h5"),
            dbc.CardBody(dcc.Graph(id='detection-freq'))
        ], className="shadow"), md=6),
        
        dbc.Col(dbc.Card([
            dbc.CardHeader("Detection Confidence", className="h5"),
            dbc.CardBody(dcc.Graph(id='confidence-hist'))
        ], className="shadow"), md=6)
    ], className="mb-4"),
    
    # Sensor Data Row
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Ultrasonic Sensor Readings", className="h5"),
            dbc.CardBody(dcc.Graph(id='ultrasonic-graph'))
        ], className="shadow"), md=6),
        
        dbc.Col(dbc.Card([
            dbc.CardHeader("Motion Status", className="h5"),
            dbc.CardBody(dcc.Graph(id='motion-graph'))
        ], className="shadow"), md=6)
    ], className="mb-4"),
    
    # System Health Row
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("System Health Status", className="h5"),
            dbc.CardBody(dcc.Graph(id='health-graph'))
        ], className="shadow"), width=12)
    ], className="mb-4"),
    
    # Data Tables Row
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Event Logs", className="h5"),
            dbc.CardBody(
                dcc.Tabs([
                    dcc.Tab(label='Detections', children=[
                        dash_table.DataTable(
                            id='detection-table',
                            columns=[{"name": i, "id": i} for i in [
                                'timestamp', 'label', 'confidence',
                                'estimated_distance_cm'
                            ]],
                            page_size=5,
                            style_table={'overflowX': 'auto'},
                            style_cell={
                                'textAlign': 'left',
                                'padding': '8px',
                                'backgroundColor': 'rgba(0,0,0,0)',
                                'color': 'white',
                                'border': '1px solid #444'
                            },
                            style_header={
                                'backgroundColor': '#2c3e50',
                                'fontWeight': 'bold'
                            },
                            filter_action="native",
                            sort_action="native"
                        )
                    ]),
                    dcc.Tab(label='Location', children=[
                        dash_table.DataTable(
                            id='location-table',
                            columns=[{"name": i, "id": i} for i in [
                                'timestamp', 'latitude', 'longitude', 
                                'speed', 'distance_meters'
                            ]],
                            page_size=5,
                            style_table={'overflowX': 'auto'},
                            style_cell={
                                'textAlign': 'left',
                                'padding': '8px',
                                'backgroundColor': 'rgba(0,0,0,0)',
                                'color': 'white',
                                'border': '1px solid #444'
                            },
                            style_header={
                                'backgroundColor': '#2c3e50',
                                'fontWeight': 'bold'
                            },
                            filter_action="native",
                            sort_action="native"
                        )
                    ]),
                    dcc.Tab(label='System Health', children=[
                        dash_table.DataTable(
                            id='health-table',
                            columns=[{"name": i, "id": i} for i in [
                                'timestamp', 'sensor_name', 'sensor_faults'
                            ]],
                            page_size=5,
                            style_table={'overflowX': 'auto'},
                            style_cell={
                                'textAlign': 'left',
                                'padding': '8px',
                                'backgroundColor': 'rgba(0,0,0,0)',
                                'color': 'white',
                                'border': '1px solid #444'
                            },
                            style_header={
                                'backgroundColor': '#2c3e50',
                                'fontWeight': 'bold'
                            },
                            filter_action="native",
                            sort_action="native"
                        )
                    ])
                ])
            )
        ], className="shadow"), width=12)
    ])
])

# =============================================
# Callbacks
# =============================================

@app.callback(
    [Output('cpu-graph', 'figure'),
     Output('mem-graph', 'figure'),
     Output('temp-graph', 'figure'),
     Output('detection-freq', 'figure'),
     Output('confidence-hist', 'figure'),
     Output('location-map', 'figure'),
     Output('battery-graph', 'figure'),
     Output('ultrasonic-graph', 'figure'),
     Output('motion-graph', 'figure'),
     Output('health-graph', 'figure'),
     Output('detection-table', 'data'),
     Output('location-table', 'data'),
     Output('health-table', 'data'),
     Output('connection-status', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_dashboard(n):
    data_dict = fetch_firebase_data()
    
    # Create connection status indicator
    if firebase_initialized:
        status = dbc.Alert("Connected to Firebase", color="success")
    else:
        status = dbc.Alert("Failed to connect to Firebase", color="danger")
    
    # Create empty figures for when no data is available
    def create_empty_fig():
        empty_fig = go.Figure()
        empty_fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font={'color': 'white'},
            margin={'l': 40, 'r': 40, 't': 30, 'b': 30},
            xaxis={'gridcolor': '#444'},
            yaxis={'gridcolor': '#444'}
        )
        empty_fig.add_annotation(text="No data available",
                                xref="paper", yref="paper",
                                x=0.5, y=0.5, showarrow=False)
        return empty_fig
    
    # System metrics figures
    system_stats = data_dict['detections'][data_dict['detections']['event_type'] == 'system_stats'].copy()
    cpu_fig = px.line(
        system_stats, x='timestamp', y='CPU',
        title='', labels={'CPU': 'Usage %'},
        color_discrete_sequence=['#1f77b4']
    ) if not system_stats.empty else create_empty_fig()
    
    mem_fig = px.line(
        system_stats, x='timestamp', y='MEM',
        title='', labels={'MEM': 'Usage %'},
        color_discrete_sequence=['#ff7f0e']
    ) if not system_stats.empty else create_empty_fig()
    
    temp_fig = px.line(
        system_stats, x='timestamp', y='TEMP',
        title='', labels={'TEMP': '°C'},
        color_discrete_sequence=['#d62728']
    ).add_hline(y=80, line_dash="dash", line_color="red") if not system_stats.empty else create_empty_fig()
    
    # Detection figures
    detections = data_dict['detections'][data_dict['detections']['event_type'] == 'detection'].copy()
    detection_freq = px.histogram(
        detections, x='timestamp', 
        title='', labels={'timestamp': 'Time'},
        color_discrete_sequence=['#2ca02c']
    ) if not detections.empty else create_empty_fig()
    
    confidence_hist = px.histogram(
        detections, x='confidence',
        title='', labels={'confidence': 'Score'},
        color_discrete_sequence=['#9467bd']
    ) if not detections.empty else create_empty_fig()
    
    # Location map
    if not data_dict['locations'].empty:
        location_map = px.scatter_mapbox(
            data_dict['locations'],
            lat='latitude',
            lon='longitude',
            hover_name='timestamp',
            zoom=15,
            height=400,
            color_discrete_sequence=['#17becf']
        )
        location_map.update_layout(
            mapbox_style="dark",
            mapbox_accesstoken="your-mapbox-token",  # You need to add your Mapbox token
            margin={"r":0,"t":0,"l":0,"b":0}
        )
    else:
        location_map = create_empty_fig()
    
    # Battery graph
    battery_fig = px.line(
        data_dict['battery'], x='timestamp', y='battery_percentage',
        title='', labels={'battery_percentage': 'Battery %'},
        color_discrete_sequence=['#7f7f7f']
    ).add_hline(y=20, line_dash="dash", line_color="red") if not data_dict['battery'].empty else create_empty_fig()
    
    # Ultrasonic sensor graph
    ultrasonic_fig = px.line(
        data_dict['ultrasonic'], x='timestamp', y='distance_cm',
        title='', labels={'distance_cm': 'Distance (cm)'},
        color_discrete_sequence=['#8c564b']
    ) if not data_dict['ultrasonic'].empty else create_empty_fig()
    
    # Motion status graph
    if not data_dict['motion'].empty:
        data_dict['motion']['motion_active'] = data_dict['motion']['motion_status'].apply(lambda x: 1 if x == 'active' else 0)
        motion_fig = px.line(
            data_dict['motion'], x='timestamp', y='motion_active',
            title='', labels={'motion_active': 'Motion Status'},
            color_discrete_sequence=['#e377c2']
        )
        motion_fig.update_yaxes(tickvals=[0, 1], ticktext=['Inactive', 'Active'])
    else:
        motion_fig = create_empty_fig()
    
    # System health graph
    if not data_dict['system_health'].empty:
        health_fig = px.scatter(
            data_dict['system_health'], x='timestamp', y='sensor_name',
            color='sensor_faults', title='',
            labels={'sensor_name': 'Sensor', 'sensor_faults': 'Fault Status'},
            color_continuous_scale='Viridis'
        )
    else:
        health_fig = create_empty_fig()
    
    # Apply consistent styling to all figures
    for fig in [cpu_fig, mem_fig, temp_fig, detection_freq, confidence_hist,
                location_map, battery_fig, ultrasonic_fig, motion_fig, health_fig]:
        if fig is not None:  # Skip None figures
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font={'color': 'white'},
                margin={'l': 40, 'r': 40, 't': 30, 'b': 30},
                xaxis={'gridcolor': '#444'},
                yaxis={'gridcolor': '#444'}
            )
    
    return (
        cpu_fig, mem_fig, temp_fig,
        detection_freq, confidence_hist,
        location_map, battery_fig,
        ultrasonic_fig, motion_fig, health_fig,
        detections.to_dict('records'),
        data_dict['locations'].to_dict('records'),
        data_dict['system_health'].to_dict('records'),
        status
    )

# =============================================
# Run the App
# =============================================

if __name__ == '__main__':
    app.run_server(debug=True, host="0.0.0.0", port=8050)