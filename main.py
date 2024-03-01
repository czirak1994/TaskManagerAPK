from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.togglebutton import ToggleButton
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.widget import Widget
from kivymd.uix.button import MDRaisedButton
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.properties import StringProperty, ObjectProperty, BooleanProperty, ListProperty
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
import sqlite3
from datetime import datetime
from functools import partial
import requests
import json
import websocket


class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super(LoginScreen, self).__init__(**kwargs)
        self.conn = sqlite3.connect('users.db')

    def login(self):
        username = self.ids.username.text
        password = self.ids.password.text

        # Connect to the database and check if the username and password match any record
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        records = c.fetchall()
        conn.close()

        if records:
            # Set the username of the MyApp class
            MyApp.username = username

            # Remove the role1 and role2 screens from the ScreenManager if they exist
            if self.manager.has_screen('role1'):
                self.manager.remove_widget(self.manager.get_screen('role1'))
            if self.manager.has_screen('role2'):
                self.manager.remove_widget(self.manager.get_screen('role2'))

            # Add the screen corresponding to the role of the user to the ScreenManager
            if records[0][2] == 'role1':
                self.manager.add_widget(Role1Screen(name='role1'))
            else:
                self.manager.add_widget(Role2Screen(name='role2'))

            # Switch to the new screen and remove the LoginScreen
            self.manager.current = records[0][2]
            self.manager.remove_widget(self.manager.get_screen('login'))
        else:
            print("Invalid username or password")  # Print statement for debugging

class CustomTask(BoxLayout):
    text = StringProperty()
    selected = BooleanProperty(False)
    default_color = ListProperty(get_color_from_hex("#333333"))
    on_release = ObjectProperty()
Builder.load_string("""
<Role2Screen>:
    ScrollView:
        do_scroll_x: False
        do_scroll_y: True
        BoxLayout:
            id: box
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            size_hint_x: 1
            spacing: 10
    BoxLayout:
        size_hint_y: None
        height: '48dp'
        MDRaisedButton:
            id: complete_button
            text: 'Complete'
            size_hint_x: 1
""")

class Role2Screen(Screen):
    def __init__(self, **kwargs):
        super(Role2Screen, self).__init__(**kwargs)
        self.selected_tasks = []  # List of selected tasks
        self.fetch_data()
        self.ids.complete_button.width = Window.width
        self.ids.complete_button.bind(on_release=self.complete_tasks)  # Bind the complete button
        self.ws = websocket.WebSocketApp("ws://127.0.0.1:8000/api/tasks/",
                                         on_message=self.on_ws_message,
                                         on_error=self.on_ws_error,
                                         on_close=self.on_ws_close)
        self.ws.on_open = self.on_ws_open
        Clock.schedule_once(lambda dt: self.ws.run_forever(), 0)
        

   
       
    def on_ws_open(self, ws):
        print("WebSocket connection opened")

    def on_ws_message(self, ws, message):
        print(f"Received message: {message}")
        # Update the UI based on the message

    def on_ws_error(self, ws, error):
        print(f"WebSocket error: {error}")
        # If the WebSocket connection fails, try to reconnect after 5 seconds

    def on_ws_close(self, ws, close_status_code, close_msg):
        print("WebSocket connection closed")
        # If the WebSocket connection is closed, try to reconnect after 5 seconds

    def on_button_press(self, instance):
        # Other code...
        # Send a message to the server when a task is selected or deselected
        self.ws.send(json.dumps({
            'task_id': instance.task_id,
            'selected': instance.state == 'down',
            'selected_by': MyApp.username
        }))
    grabbed_task = ObjectProperty(None, allownone=True)

    def grab_selected_task(self, instance):
        if not self.selected_tasks or self.grabbed_task:
            # If there's no selected task or there's already a grabbed task, do nothing
            return
        # Get the first selected task
        task = self.selected_tasks[0]
        # Change the color of the task
        task.rect_color.rgba = get_color_from_hex('#FFFF00')  # Yellow color
        # Store the grabbed task
        self.grabbed_task = task
        # Clear the selected tasks
        self.selected_tasks.clear()

    def release_task(self):
        if self.grabbed_task:
            # Reset the color of the task
            self.grabbed_task.rect_color.rgba = [1, 1, 1, 1]  # Original color
            # Clear the grabbed task
            self.grabbed_task = None
    def fetch_data(self):
    # Send a GET request to the Django server
        response = requests.get('http://127.0.0.1:8000/api/tasks/')
        if response.status_code == 200:
            tasks = response.json()
            for task in tasks:
                if not task['completed']:
                    btn = TaskButton(text=str(task['title']), size_hint_y=None, height=50, size_hint_x=1)
                    btn.task_id = task['id']  # Store the task ID in the button
                    btn.title = task['title']  # Store the task title in the button
                    btn.description = task['description']  # Store the task description in the button
                    btn.created_at = task['created_at']  # Store the task creation time in the button
                    btn.updated_at = task['updated_at']  # Store the task update time in the button
                    btn.created_by = task['created_by']  # Store the task creator in the button
                    btn.completed_by = task['completed_by']  # Store the task completer in the button
                    btn.bind(on_press=self.on_button_press)
                    self.ids.box.add_widget(btn)
        else:
            print(f"Failed to fetch tasks: {response.status_code}")  # Print statement for debugging

    def on_button_press(self, instance):
        if instance == self.grabbed_task:
            return
        if instance.state == 'down':
            instance.md_bg_color = get_color_from_hex("#0095c2")  # Red color when selected
            self.selected_tasks.append(instance)  # Add the selected task to the list
        else:
            instance.background_color = (1, 1, 1, 1)  # White color when not selected
            self.selected_tasks.remove(instance)  # Remove the task from the list

    def complete_tasks(self, instance):
        for task in self.selected_tasks:
            headers = {'Content-Type': 'application/json'}  # Set the content type to 'application/json'
            data = json.dumps({
                'completed': 'true', 
                'title': task.title, 
                'description': task.description,
                'created_by': task.created_by,
                'completed_by': MyApp.username,  # Use the current user as the completer
                'completed_at': datetime.now().isoformat()  # Use the current time as the completion time
            })  # Convert the data to JSON
            response = requests.put(f"http://127.0.0.1:8000//api/tasks/{task.task_id}/", data=data, headers=headers)
            if response.status_code == 200:
                self.ids.box.remove_widget(task)  # Remove the task from the GUI
            else:
                print(f"Failed to complete task: {response.status_code}")  # Print statement for debugging
                print(f"Response body: {response.text}")  # Print the response body
        self.selected_tasks.clear()  # Clear the list of selected tasks

class TaskButton(ToggleButton):
    def __init__(self, **kwargs):
        super(TaskButton, self).__init__(**kwargs)
        self.bind(state=self.on_state, pos=self.update_rect, size=self.update_rect)

        with self.canvas.before:
            self.rect_color = Color(1, 1, 1, 1)  # Default color is white
            self.rect = Rectangle(size=self.size, pos=self.pos)

    def on_state(self, instance, value):
        if value == 'down':
            self.rect_color.rgba = get_color_from_hex("#0095c2")  # Red color when selected
        else:
            self.rect_color.rgba = [1, 1, 1, 1]  # White color when not selected

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class Role1Screen(Screen):
    def __init__(self, **kwargs):
        super(Role1Screen, self).__init__(**kwargs)
        self.selected_tasks = []
        self.task_buttons = {}
        Clock.schedule_once(self.add_task_buttons, 1)  # add a delay of 1 second

    def add_task_buttons(self, dt):
        self.task_buttons['1 pal. 6427-es KLT a CNC területre'] = self.ids.task1
        self.task_buttons['1 pal. 6427-es KLT a CMT területre'] = self.ids.task2
        self.task_buttons['Késztermék szállítása raktárba a Porsche-Kovomo területről'] = self.ids.task3
        self.task_buttons['114 333-as box a Kovomo területre'] = self.ids.task4
        self.task_buttons['1 pal. 6280-as KLT Kovomo területre'] = self.ids.task5
        self.task_buttons['Késztermék szállítása raktárba a Wielpütz területről'] = self.ids.task6
        self.task_buttons['Késztermék szállítása raktárba a ATL területről'] = self.ids.task7
        self.task_buttons['1 pal. 4280-as KLT ATL területre'] = self.ids.task8
        self.task_buttons['1 pal. 6280-as KLT ATL területre'] = self.ids.task9
        self.task_buttons['1 pal. 6280-as KLT Wielpütz területre'] = self.ids.task10
        self.task_buttons['1 pal. 6280-as KLT(BEN001) Wielpütz területre'] = self.ids.task11
        self.task_buttons['Hegesztett termék szállítása Vége.ell. pódiumról a forrasztásra'] = self.ids.task12
        self.task_buttons['Pasztázott Conti szállítása forrasztásra'] = self.ids.task13
        self.task_buttons['1 pal. P008-as KLT Porsche területre'] = self.ids.task14
        self.task_buttons['1 pal. p016-os KLT Porsche területre'] = self.ids.task15
        self.task_buttons['Félkész termék szállítása raktárba Daimler területről'] = self.ids.task16
        self.task_buttons['Félkész termék szállítása raktárba Wielpütz területről'] = self.ids.task17
        self.task_buttons['Félkész termék szállítása raktárba Amarok területről'] = self.ids.task18
        self.task_buttons['Félkész termék szállítása raktárba BMW területről'] = self.ids.task19
        self.task_buttons['Utómunka szállítása kemencére BMW területről'] = self.ids.task20


    def select_task(self, instance):
        task_name = instance.text
        if task_name not in self.selected_tasks:
            self.selected_tasks.append(task_name)
            instance.md_bg_color = get_color_from_hex("#0095c2")  # Change color to red when selected
            print(f"Task {task_name} selected")  # Print statement for debugging
        else:
            self.selected_tasks.remove(task_name)
            instance.md_bg_color = get_color_from_hex("#333333")  # Change color back to white when deselected
            print(f"Task {task_name} deselected")  # Print statement for debugging

    def send_tasks(self):
        current_time = datetime.now()
        if self.selected_tasks:
            for task_name in list(self.selected_tasks):  # Create a copy of the list for iteration
                # Send a POST request to the Django server
                response = requests.post('http://127.0.0.1:8000/api/tasks/', data={
                    'title': task_name,
                    'description': 'This is a task from the Kivy app.',
                    'completed': False,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat(),
                    "created_by" : MyApp.username
                })
                if response.status_code == 201:
                    # Remove the task from the selected_tasks list
                    self.selected_tasks.remove(task_name)
                    # Change the color of the task button back to white
                    self.task_buttons[task_name].md_bg_color = get_color_from_hex("#333333")
                    print(f"Task {task_name} sent")  # Print statement for debugging
                else:
                    print(f"Failed to send task {task_name}")  # Print statement for debugging
            print("Tasks sent")  # Print statement for debugging
        else:
            print("No tasks selected")  # Print statement for debugging

class MyApp(MDApp):
    username = StringProperty(None)

    def build(self):
        Window.clearcolor = (0.2, 0.2, 0.2, 1)

        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(Role1Screen(name='role1'))
        sm.add_widget(Role2Screen(name='role2'))
        return sm

if __name__ == '__main__':
    MyApp().run()