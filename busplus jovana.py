from tkinter import *
import psycopg2 as pg
import tkinter as tk
from collections import defaultdict


class Busplus:
    def __init__(self):
        self.con = pg.connect(
            database='BusPlus',
            host='localhost',
            port='5432',
            user='postgres',
            password='Yoyoba22'
        )
        self.stations = self.fetch_station_data()

    def fetch_station_data(self):
        cursor = self.con.cursor()
        cursor.execute("SELECT naziv_stanice, x_osa, y_osa FROM bus_stanice")
        station_data = cursor.fetchall()

        stations = {}
        for row in station_data:
            station_name, x, y = row
            stations[station_name] = (x, y)

        cursor.close()
        return stations

    def fetch_route_data(self):
        cursor = self.con.cursor()
        cursor.execute("SELECT pocetna_stanica_id, krajnja_stanica_id, trajanje, bus_id FROM Rute")
        route_data = cursor.fetchall()

        routes = defaultdict(dict)

        for row in route_data:
            start_station_id, end_station_id, duration, bus_id = row
            start_station = self.get_station_name_by_id(start_station_id)
            end_station = self.get_station_name_by_id(end_station_id)

            if start_station and end_station:
                duration_seconds = self.time_to_seconds(duration)
                routes[start_station][end_station] = (duration_seconds, bus_id)
            else:
                print(f"Netacan naziv stanice: {start_station_id}, {end_station_id}")

        cursor.close()
        return routes

    def time_to_seconds(self, time_obj):
        return time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second

    def get_station_name_by_id(self, station_id):
        cursor = self.con.cursor()
        cursor.execute("SELECT naziv_stanice FROM bus_stanice WHERE id_stanice = %s", (station_id,))
        result = cursor.fetchone()
        cursor.close()
        if result:
            return result[0]
        return None

    def calculate_fastest_route(self, start_station, end_station):
        graph = self.fetch_route_data()

        if start_station not in graph or end_station not in graph:
            print("Start or end station is not in the graph.")
            return None, None, None

        visited = set()
        shortest_durations = {station: (float('inf'), None) for station in graph}
        shortest_durations[start_station] = (0, None)
        station_route = {}

        while True:
            current_station = None
            current_duration = float('inf')
            current_bus_id = None

            for station, (duration, bus_id) in shortest_durations.items():
                if duration < current_duration and station not in visited:
                    current_station = station
                    current_duration = duration
                    current_bus_id = bus_id

            if current_station is None:
                break

            visited.add(current_station)

            for neighbor, (neighbor_duration, neighbor_bus_id) in graph[current_station].items():
                if neighbor in shortest_durations:
                    total_duration = current_duration + neighbor_duration
                    if total_duration < shortest_durations[neighbor][0]:
                        shortest_durations[neighbor] = (total_duration, neighbor_bus_id)
                        station_route[neighbor] = current_station

        if end_station not in shortest_durations:
            print("Nijedna ruta nije pronadjena.")
            return None, None, None

        travel_time_minutes = shortest_durations[end_station][0] / 60
        bus_id = shortest_durations[end_station][1]

        current_station = end_station
        route_stations = [end_station]
        while current_station != start_station:
            current_station = station_route[current_station]
            route_stations.append(current_station)

        return travel_time_minutes, list(reversed(route_stations)), bus_id
        
    def display_route_details(self, start_station, end_station):
        global bus_line
        travel_time, stations_passed_through, bus_id = self.calculate_fastest_route(start_station, end_station)

        if travel_time is not None:
            result_window = tk.Toplevel(root)
            result_window.title("Najbliza ruta:")

            travel_time_label = tk.Label(result_window, text=f"Vreme putovanja: {travel_time:.2f} minuta")
            travel_time_label.pack()


            bus_id_label = tk.Label(result_window)
            bus_id_label.pack()

            stations_label = tk.Label(result_window, text="Ruta:")
            stations_label.pack()

            for station in stations_passed_through:
                station_id = self.get_station_id_by_name(station)
                station_name, bus_line = self.get_station_info(station_id)
                station_info_label = tk.Label(result_window, text=f"{station_name} ({bus_line})")
                station_info_label.pack()

    def get_station_id_by_name(self, station_name):
        cursor = self.con.cursor()
        cursor.execute("SELECT id_stanice FROM bus_stanice WHERE naziv_stanice = %s", (station_name,))
        result = cursor.fetchone()
        cursor.close()
        if result:
            return result[0]
        return None

    def get_station_info(self, station_id):
        cursor = self.con.cursor()
        cursor.execute("""
            SELECT s.naziv_stanice, r.bus_id
            FROM bus_stanice s
            JOIN Rute r ON s.id_stanice = r.pocetna_stanica_id OR s.id_stanice = r.krajnja_stanica_id
            WHERE s.id_stanice = %s
        """, (station_id,))
        result = cursor.fetchone()
        cursor.close()
        if result:
            station_name, bus_id = result
            bus_line_name = self.get_bus_line_name(bus_id)
            return station_name, bus_line_name
        return None, None



    def get_bus_line_name(self, bus_id):
        cursor = self.con.cursor()
        cursor.execute("SELECT naziv_linije FROM bus_linije WHERE bus_id = %s", (bus_id,))
        result = cursor.fetchone()
        cursor.close()
        if result:
            return result[0]
        return None

bus_plus = Busplus()

root = tk.Tk()
root.title('BusPlus')

def is_point_on_line(x1, y1, x2, y2, x, y):
    line_length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    
    dist1 = ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
    dist2 = ((x - x2) ** 2 + (y - y2) ** 2) ** 0.5
    
    return abs(dist1 + dist2 - line_length) < 1e-6

def find_intersection(x1, y1, x2, y2, x3, y3, x4, y4):
    det = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if det == 0:
        return None
    x = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / det
    y = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / det

    if is_point_on_line(x1, y1, x2, y2, x, y):
        return x, y
    return None

c = tk.Canvas(width=400, height=400, bg='lightgreen')
c.pack()
line_AB = c.create_line(40, 100, 350, 100, fill='blue')
c.create_text(50, 90, text='Linija A', fill='blue')
c.create_oval(220-3,100-3,220+3,100+3, fill='blue')
c.create_text(220,90,text='Stanica 4',fill='blue')
line_BC = c.create_line(100, 46, 350, 300, fill='green')
c.create_text(100, 40, text='Linija B', fill='green')
c.create_oval(350-3,300-3,350+3,300+3, fill='green')
c.create_text(370,320,text='Stanica 5',fill='green')
line_CA = c.create_line(150, 300, 300, 50, fill='red')
c.create_text(300, 40, text='Linija C', fill='red')
c.create_oval(180-3,250-3,180+3,250+3, fill='red')
c.create_text(200,260,text='Stanica 6',fill='red')


intersection_AB = find_intersection(40, 100, 350, 100, 100, 46, 350, 300)
intersection_BC = find_intersection(100, 46, 350, 300, 150, 300, 300, 50)
intersection_CA = find_intersection(150, 300, 300, 50, 40, 100, 350, 100)

dot_to_station = {}
for point, color in [(intersection_AB, 'blue'), (intersection_BC, 'green'), (intersection_CA, 'red')]:
    if point is not None:
        dot_to_station[color] = 'Intersection'

line_AB_color = c.itemcget(line_AB, 'fill')
line_BC_color = c.itemcget(line_BC, 'fill')
line_CA_color = c.itemcget(line_CA, 'fill')

dot_to_station = {
    'blue': 'Stanica 1',
    'red': 'Stanica 2',
    'green': 'Stanica 3'
}

stations = {
    'Stanica 1': (50, 100),
    'Stanica 2': (350, 46),
    'Stanica 3': (300, 300),
    'Stanica 4': (290, 100),
    'Stanica 5': (170, 190),
    'Stanica 6': (180, 250)
}

def add_stanica_prefix(entry):
    entry.insert(0, "stanica ")

label_izracunaj = Label(root, text='Izracunaj udaljenost')
label_pocetna = Label(root, text='Pocetna Stanica')
label_krajnja = Label(root, text='Krajnja Stanica')
entry_pocetna = Entry(root)
entry_krajnja = Entry(root)

add_stanica_prefix(entry_pocetna)
add_stanica_prefix(entry_krajnja)

label_izracunaj.pack()
label_pocetna.pack()
entry_pocetna.pack()
label_krajnja.pack()
entry_krajnja.pack()

def calculate_route():
    start_station_input = entry_pocetna.get()
    end_station_input = entry_krajnja.get()

    if not start_station_input or not end_station_input:
        print("Unesite i pocetnu i krajnju stanicu.")
        return

    start_station_exists = False
    end_station_exists = False

    for station_name in bus_plus.stations.keys():
        if station_name.lower() == start_station_input.lower() or station_name.lower() == f"stanica {start_station_input.lower()}":
            start_station_input = station_name
            start_station_exists = True
            break

    for station_name in bus_plus.stations.keys():
        if station_name.lower() == end_station_input.lower() or station_name.lower() == f"stanica {end_station_input.lower()}":
            end_station_input = station_name
            end_station_exists = True
            break

    if not start_station_exists or not end_station_exists:
        print("Stanica nepostojeca.")
        return

    bus_plus.display_route_details(start_station_input, end_station_input)



calculate_button = Button(root, text='Izračunaj', command=calculate_route)
calculate_button.pack()

dot_size = 3
for point, color in [(intersection_AB, line_AB_color), (intersection_BC, line_BC_color), (intersection_CA, line_CA_color)]:
    if point is not None:
        x, y = point
        station_name = dot_to_station.get(color, 'Unknown')
        c.create_oval(x - dot_size, y - dot_size, x + dot_size, y + dot_size, fill=color)
        c.create_text(x, y - dot_size - 10, text=station_name, fill=color)


root.mainloop()