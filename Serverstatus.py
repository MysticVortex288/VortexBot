import os
import logging
import time
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from mcstatus import JavaServer
import socket

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "minecraft_server_status_secret_key")

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/setup/<server_address>', methods=['GET'])
def setup(server_address):
    """Setup the server to check"""
    if not server_address:
        flash('Bitte gib eine Server-Adresse ein', 'danger')
        return redirect(url_for('index'))
    
    # Save the server address in session
    session['server_address'] = server_address
    session['setup_time'] = time.time()
    
    return render_template('setup_success.html', server_address=server_address)

@app.route('/status', methods=['GET'])
def status():
    """Check and display the status of the configured server"""
    server_address = session.get('server_address')
    
    if not server_address:
        flash('Bitte richte zuerst einen Server mit /setup ein', 'warning')
        return redirect(url_for('index'))
    
    # Check the server status
    status_data = check_minecraft_server(server_address)
    
    # Render the status page
    return render_template('status.html', server_address=server_address, status_data=status_data)

@app.route('/check_server', methods=['POST'])
def check_server():
    """API endpoint to check the status of a Minecraft server"""
    server_address = request.form.get('server_address')
    
    if not server_address:
        return jsonify({
            'status': 'error',
            'message': 'Bitte gib eine Server-Adresse ein'
        })
    
    result = check_minecraft_server(server_address)
    return jsonify(result)

def check_minecraft_server(server_address):
    """Check the status of a Minecraft server"""
    try:
        # Parse the server address (handle optional port)
        if ':' in server_address:
            host, port_str = server_address.split(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                port = 25565  # Default Minecraft port
        else:
            host = server_address
            port = 25565
        
        # Create server instance
        server = JavaServer(host, port)
        
        # Query server status
        status = server.status()
        
        # Query online players (if available)
        try:
            query = server.query()
            players = query.players.names
        except:
            # If query fails, use basic status info
            players = []
            logging.debug("Server query failed, using basic status info")
        
        # Format response data
        response = {
            'status': 'online',
            'latency': round(status.latency, 2),
            'version': status.version.name,
            'protocol': status.version.protocol,
            'motd': status.description,
            'players_online': status.players.online,
            'players_max': status.players.max,
            'players_list': players
        }
        
        return response
        
    except socket.timeout:
        return {
            'status': 'error',
            'message': 'Zeitüberschreitung der Verbindung. Server ist möglicherweise offline oder blockiert Anfragen.'
        }
    except socket.gaierror:
        return {
            'status': 'error',
            'message': 'Ungültige Server-Adresse oder Hostname konnte nicht aufgelöst werden.'
        }
    except ConnectionRefusedError:
        return {
            'status': 'error',
            'message': 'Verbindung abgelehnt. Server ist möglicherweise offline oder blockiert Anfragen.'
        }
    except Exception as e:
        logging.error(f"Fehler bei der Serverprüfung: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'message': f'Fehler bei der Serverprüfung: {str(e)}'
        }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
