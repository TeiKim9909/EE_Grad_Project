# -*- coding: utf-8 -*- # Explicitly declare UTF-8 encoding
import kivy

kivy.require("2.0.0")  # Specify Kivy version requirement (adjust as needed)

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.properties import (
    StringProperty,
    ListProperty,
    ObjectProperty,
    OptionProperty,
    NumericProperty,
    BooleanProperty,
)  # Import BooleanProperty
from kivy.clock import Clock
from kivy.utils import get_color_from_hex
import time
import datetime  # Import datetime for time comparison
import os

from sleep_detector import SleepDetector
from controller import Controller

# --- Pretendard 폰트 설정 ---
from kivy.core.text import LabelBase

try:
    # Adjust 'fn_regular' to the exact filename of your Pretendard font file
    LabelBase.register(name="Pretendard", fn_regular="font/Pretendard-Regular.otf")
    print("Pretendard font registered successfully.")
except Exception as e:
    print(f"Error registering font: {e}")
    print(
        "Ensure 'Pretendard-Regular.ttf' (or your Pretendard font file) is in the same directory as main.py"
    )
# ---------------------


# --- Time Picker Popup ---
class TimePickerPopup(Popup):
    """Popup for selecting hour and minute."""

    target_property = StringProperty("")  # 'sleep_time' or 'wakeup_time'
    app_ref = ObjectProperty(None)
    selected_hour = NumericProperty(0)
    selected_minute = NumericProperty(0)

    def __init__(self, target_property, current_time, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.target_property = target_property
        self.app_ref = app_ref
        # Parse current time to set initial selection
        try:
            # Use datetime to parse reliably
            parsed_time = datetime.datetime.strptime(current_time, "%I:%M %p")
            self.selected_hour = parsed_time.hour
            self.selected_minute = parsed_time.minute
        except Exception as e:
            print(f"Error parsing initial time '{current_time}': {e}")
            now = datetime.datetime.now()
            self.selected_hour = now.hour
            self.selected_minute = now.minute

        # Populate hour and minute selectors
        self.populate_selector(self.ids.hour_grid, 24, "hour")
        self.populate_selector(self.ids.minute_grid, 60, "minute")
        # Scroll to initial selection (needs slight delay for layout)
        Clock.schedule_once(self.scroll_to_initial, 0.1)

    def populate_selector(self, grid, count, type):
        """Fills the GridLayout with number buttons."""
        for i in range(count):
            # *** Ensure buttons inside popup also use the font ***
            btn = Button(
                text=f"{i:02d}", size_hint_y=None, height="40dp", font_name="Pretendard"
            )
            if type == "hour":
                btn.bind(on_press=lambda instance, h=i: self.set_hour(h))
                if i == self.selected_hour:
                    btn.background_color = get_color_from_hex(
                        "#555555"
                    )  # Highlight initial
            else:  # minute
                btn.bind(on_press=lambda instance, m=i: self.set_minute(m))
                if i == self.selected_minute:
                    btn.background_color = get_color_from_hex(
                        "#555555"
                    )  # Highlight initial
            grid.add_widget(btn)

    def scroll_to_initial(self, dt):
        """Scrolls the ScrollViews to the initially selected time."""
        # Check if ids dictionary is populated before accessing
        if not self.ids:
            print("Warning: TimePickerPopup ids not ready for scrolling.")
            return
        hour_scroll = self.ids.get("hour_scroll")
        minute_scroll = self.ids.get("minute_scroll")
        hour_grid = self.ids.get("hour_grid")
        minute_grid = self.ids.get("minute_grid")

        if not all([hour_scroll, minute_scroll, hour_grid, minute_grid]):
            print("Warning: Scroll elements not found in TimePickerPopup.")
            return

        # Calculate scroll position (0=top, 1=bottom)
        # Approximation: scroll_y = 1.0 - (selected_index / total_items)
        if len(hour_grid.children) > 0:
            # Kivy GridLayout children are ordered bottom-to-top visually, but index 0 is the last added (top)
            # We need the visual index, which is reversed
            visual_index = len(hour_grid.children) - 1 - self.selected_hour
            scroll_y_hour = 1.0 - (
                visual_index / (len(hour_grid.children) - 1)
                if len(hour_grid.children) > 1
                else 0
            )
            hour_scroll.scroll_y = max(
                0, min(1, scroll_y_hour)
            )  # Clamp between 0 and 1

        if len(minute_grid.children) > 0:
            visual_index_minute = len(minute_grid.children) - 1 - self.selected_minute
            scroll_y_minute = 1.0 - (
                visual_index_minute / (len(minute_grid.children) - 1)
                if len(minute_grid.children) > 1
                else 0
            )
            minute_scroll.scroll_y = max(
                0, min(1, scroll_y_minute)
            )  # Clamp between 0 and 1

    def set_hour(self, hour):
        self.selected_hour = hour
        print(f"Hour selected: {hour}")
        # Update button appearance (optional)
        if self.ids and self.ids.get("hour_grid"):
            for btn in self.ids.hour_grid.children:
                try:
                    if int(btn.text) == hour:
                        btn.background_color = get_color_from_hex("#555555")
                    else:
                        btn.background_color = [1, 1, 1, 1]  # Default Kivy Button color
                except ValueError:
                    pass

    def set_minute(self, minute):
        self.selected_minute = minute
        print(f"Minute selected: {minute}")
        # Update button appearance (optional)
        if self.ids and self.ids.get("minute_grid"):
            for btn in self.ids.minute_grid.children:
                try:
                    if int(btn.text) == minute:
                        btn.background_color = get_color_from_hex("#555555")
                    else:
                        btn.background_color = [1, 1, 1, 1]
                except ValueError:
                    pass

    def confirm_selection(self):
        """Updates the target property in the main app and closes."""
        hour = self.selected_hour
        minute = self.selected_minute

        # Convert to AM/PM format for display
        temp_time = datetime.time(hour=hour, minute=minute)
        formatted_time_12 = temp_time.strftime("%I:%M %p").lstrip(
            "0"
        )  # Remove leading zero from hour

        if self.app_ref and hasattr(self.app_ref, self.target_property):
            setattr(self.app_ref, self.target_property, formatted_time_12)
            print(f"Set {self.target_property} to {formatted_time_12}")
            # Reset triggered flag when time is changed
            if self.target_property == "sleep_time":
                self.app_ref.sleep_alarm_triggered = False
            elif self.target_property == "wakeup_time":
                self.app_ref.wakeup_alarm_triggered = False
        self.dismiss()


# --- Alarm Ringing Popup ---
class AlarmRingingPopup(Popup):
    """Popup that appears when an alarm time is reached."""

    current_time_str = StringProperty("")
    weather_icon = StringProperty("icon/sunny.png")  # Placeholder icon (e.g., sunny)
    temp_info = StringProperty("--°C / --°C")  # Placeholder temps

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set current time when popup opens
        # change format to 12-hour with AM/PM in the front
        self.current_time_str = (
            datetime.datetime.now().strftime("%p  %I:%M").lstrip("0")
        )
        # Placeholder for fetching weather data
        self.fetch_weather_placeholder()

    def fetch_weather_placeholder(self):
        """Placeholder function to simulate fetching weather."""
        # In a real app, you would make an API call here
        # Based on the response, update self.weather_icon and self.temp_info
        # Example placeholders:
        conditions = ["맑음", "흐림", "비", "눈"]
        icon_folder = "icon"
        import random

        current_condition = random.choice(conditions)

        if current_condition == "맑음":
            self.weather_icon = os.path.join(icon_folder, "sunny.png")
        elif current_condition == "흐림":
            self.weather_icon = os.path.join(icon_folder, "cloudy.png")
        elif current_condition == "비":
            self.weather_icon = os.path.join(icon_folder, "rainy.png")
        elif current_condition == "눈":
            self.weather_icon = os.path.join(icon_folder, "snowman.png")
        else:
            self.weather_icon = os.path.join(icon_folder, "sunny.png")

        print(f"Weather condition: {self.weather_icon}")

        max_temp = random.randint(5, 30)
        min_temp = random.randint(-5, max_temp - 5)
        self.temp_info = f"{max_temp}°C / {min_temp}°C"


class AlarmClockLayout(FloatLayout):
    """Root layout for the alarm clock app."""

    current_time = StringProperty("")
    selected_menu = OptionProperty("Clock", options=["Clock", "Alarm"])
    brightness_level = NumericProperty(50)
    sleep_time = StringProperty("11:50 PM")
    wakeup_time = StringProperty("07:30 AM")
    # *** Flags to prevent multiple alarm popups ***
    sleep_alarm_triggered = BooleanProperty(
        False
    )  # Keep sleep flag for potential future use or reset logic
    wakeup_alarm_triggered = BooleanProperty(False)
    # *** Property to hold the currently active alarm popup ***
    active_alarm_popup = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.controller = Controller()
        self.sleep_detector = SleepDetector()
        Clock.schedule_interval(self.run_sleep_detection, 300)
        # Check alarm every second (could be less frequent)
        Clock.schedule_interval(self.check_alarms, 1)
        Clock.schedule_interval(self.update_time, 1)  # Keep updating clock display
        self.update_time(0)

    def run_sleep_detection(self, dt):
        """
        Runs the sleep detection logic from the SleepDetector instance.
        """
        detection_result = self.sleep_detector.detect()
        if detection_result == 1:  # Sleep detected
            # TODO: Pull blind 100% down
            pass
        elif detection_result == 0:  # Wakefulness detected
            pass
        else:
            ValueError("Invalid detection result")

    def check_alarms(self, dt):
        """Checks if the current time matches the wakeup alarm time."""
        now = datetime.datetime.now()
        current_hm = now.strftime("%I:%M %p").lstrip("0")  # Format: H:MM AM/PM

        # Check Wakeup Alarm
        # *** Changed 'elif' to 'if' ***
        if current_hm == self.wakeup_time and not self.wakeup_alarm_triggered:
            print(f"Wakeup Alarm Triggered at {self.wakeup_time}")
            self.show_alarm_ringing_popup()
            self.wakeup_alarm_triggered = True  # Set flag
        elif current_hm == self.wakeup_time and self.wakeup_alarm_triggered:
            pass
        else:
            try:
                wakeup_time = datetime.datetime.strptime(self.wakeup_time, "%I:%M %p")
                current_time = datetime.datetime.strptime(current_hm, "%I:%M %p")
                time_diff = (wakeup_time - current_time).total_seconds() / 60
                if 4.9 <= time_diff <= 5.1 and not self.wakeup_alarm_triggered:
                    print(f"5 minutes before wakeup time: {self.wakeup_time}")
                    # TODO: Add blind control logic here
            except ValueError as e:
                print(f"Error comparing times: {e}")

        # Reset flags slightly after the minute changes to allow re-triggering next day
        # Or reset when the alarm time is changed
        if now.second == 1:  # Reset flags at the start of the next minute
            # Still reset sleep flag in case it's used elsewhere or re-enabled later
            if current_hm != self.sleep_time:
                self.sleep_alarm_triggered = False
            if current_hm != self.wakeup_time:
                self.wakeup_alarm_triggered = False

    def show_alarm_ringing_popup(self):
        """Shows the alarm ringing popup, preventing duplicates."""
        # Dismiss any existing alarm popup first
        if self.active_alarm_popup:
            self.active_alarm_popup.dismiss()

        popup = AlarmRingingPopup(title="")  # Title for the ringing popup
        # Store reference to the active popup
        self.active_alarm_popup = popup
        # Clear reference when dismissed
        popup.bind(on_dismiss=self.clear_active_popup)
        popup.open()

    def clear_active_popup(self, instance):
        """Callback function to clear the active popup reference."""
        if self.active_alarm_popup == instance:
            self.active_alarm_popup = None

    def update_time(self, dt):
        """Updates the current_time property for the main clock display."""
        try:
            # Use consistent formatting
            self.current_time = datetime.datetime.now().strftime("%I:%M %p").lstrip("0")
        except Exception as e:
            print(f"Error updating time: {e}")
            self.current_time = "Error"

    def select_menu(self, menu_name):
        """Updates the selected menu state."""
        print(f"{menu_name} menu selected")
        self.selected_menu = menu_name

    def open_time_picker(self, target_property):
        """Opens the time picker popup for the specified target."""
        current_value = getattr(self, target_property)
        popup = TimePickerPopup(
            target_property=target_property,
            current_time=current_value,
            app_ref=self,
        )
        popup.open()

    def increase_brightness(self):
        """Increases brightness by 5, max 100."""
        self.brightness_level = min(100, self.brightness_level + 5)
        print(f"Brightness increased to: {self.brightness_level}%")
        # TODO: Add blind control logic (move blinds up till brightness level is reached)
        # If max brightness is 100 and reeived brightness level is 50, with brightness level 50, move blinds to 100% up

    def decrease_brightness(self):
        """Decreases brightness by 5, min 0."""
        self.brightness_level = max(0, self.brightness_level - 5)
        print(f"Brightness decreased to: {self.brightness_level}%")
        # TODO: Add blind control logic (move blinds down till brightness level is reached)
        # If max brightness is 100 and reeived brightness level is 50, with brightness level 25, move blinds to 50% up

    def move_selection_up(self):
        """Placeholder for list navigation."""
        print("Move Up (Not implemented)")
        # TODO: Move blinds up while up button is pressed

    def move_selection_down(self):
        """Placeholder for list navigation."""
        print("Move Down (Not implemented)")
        # TODO: Move blinds down while down button is pressed


class AlarmClockApp(App):
    """Main Kivy application class."""

    title = ""  # This will remove the title text

    def build(self):
        return AlarmClockLayout()


if __name__ == "__main__":
    AlarmClockApp().run()
