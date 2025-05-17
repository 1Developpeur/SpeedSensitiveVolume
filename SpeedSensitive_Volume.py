"""
Speed Sensitive Volume, made by 1Developpeur (https://github.com/1Developpeur)
Auto-adjust music volume based on speed in Assetto Corsa.
Supports Spotify/VLC/etc.
Choose from 4 volume curves. 
Plug & play.
"""

import ac
import acsys
import os
import subprocess
import time
import math
import configparser

music_apps = [
            "Spotify", "Deezer", "Tidal", "AppleMusic",
            "Amazon Music", "YouTube Music", "Pandora",
            "SoundCloud", "VLC"
        ]

running_apps = []
new_scan = False
enabled = True
enabled_changed = False
width, height = 295, 180

is_config_menu_opened = False
is_config_menu_opened_changed = False

config_update = False
config_reset = False

class Config:
    def __init__(self) -> None:
        self.configPath = r"apps/python/SpeedSensitive_Volume/config.ini"
        self.config = configparser.ConfigParser()
        self.config.read(self.configPath)
    
    def get(self, section="SpeedSensitiveVolume", option=""):
        return self.config.getint(section, option)
    
    def set(self, section="SpeedSensitiveVolume", option="", value=None):
        self.config.set(section, option, str(value))
        self.config.write(open(self.configPath, 'w'))

class SpeedSensitiveVolume:
    def __init__(self) -> None:
        self.app_name = "Speed-Sensitive Volume Plugin"
        self.app_window = 0
        self.speed_label = 0
        self.volume_label = 0
        self.svv_path = r"apps/python/SpeedSensitive_Volume/SoundVolumeView.exe"
        
        self.config = Config()
        
        # Configuration
        self.min_speed = self.config.get(option="min_speed")     # Volume starts increasing above this speed (km/h)
        self.max_speed = self.config.get(option="max_speed")     # Maximum speed for max volume (km/h)
        self.min_volume = self.config.get(option="min_volume")   # Minimum volume (0-100)
        self.max_volume = self.config.get(option="max_volume")   # Maximum volume (0-100)
        self.scan_delay = self.config.get(option="scan_delay")   # 500ms delay between speed scans
        
        self.apps_ids = []
        self.apps_labels = []
        self.last_time = self.get_time()
        self.last_volume = self.min_volume
        self.config_menu_items = []
        self.debug = False
        if self.debug:
            self.debug_file = open("volume_calculations.txt", "w")
    
    def scan_processes(*args):
        global running_apps, music_apps, new_scan
        new_scan = True
        try:
            running_apps.clear()
            process = subprocess.Popen(
                ['tasklist'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                shell=True
            )
            stdout, _ = process.communicate()

            for app in music_apps:
                if app.lower().encode() in stdout.lower():
                    running_apps.append(app)

            #ac.log("Scanned successfully")
        except Exception as e:
            ac.log("Process scan error: {0}".format(str(e)))
    
    def get_time(self):
        return round(time.time()*1000)
    
    def acMain(self, ac_version):
        global running_apps, enabled
        self.app_window = ac.newApp(self.app_name)
        ac.setSize(self.app_window, 295, 180)
        
        author = ac.addLabel(self.app_window, "Made by 1Developpeur on Github")
        ac.setPosition(author, 35, 19)
        
        # - Scan music apps button
        btn = ac.addButton(self.app_window, "Scan music apps")
        ac.addOnClickedListener(btn, SpeedSensitiveVolume.scan_processes)
        ac.setSize(btn, 120, 25)
        ac.setFontAlignment(btn, "center")
        ac.setPosition(btn, 5, 100)
        
        # - Loaded music apps list
        lbl_1 = ac.addLabel(self.app_window, "Enabled for:")
        ac.setFontSize(lbl_1, 18)
        ac.setPosition(lbl_1, 15, 40)

        # - Enable/Disable the plugin
        self.enable_button = ac.addButton(self.app_window, "Disable" if enabled else "Enable")
        ac.addOnClickedListener(self.enable_button, SpeedSensitiveVolume.enable_button_callback)
        ac.setSize(self.enable_button, 70, 25)
        ac.setFontAlignment(self.enable_button, "center")
        ac.setPosition(self.enable_button, 130, 100)
        
        # - Volume label indicator
        self.volume_label = ac.addLabel(self.app_window, "Volume: {0}%".format(str(self.min_volume)))
        ac.setPosition(self.volume_label, 5, 130)
        ac.setFontSize(self.volume_label, 16)
        
        # - Volume progress bar indicator
        self.progress_bar_volume = ac.addProgressBar(self.app_window, "Volume level")
        ac.setPosition(self.progress_bar_volume, 130, 130)
        ac.setSize(self.progress_bar_volume, 150, 20)
        ac.setValue(self.progress_bar_volume, self.min_volume/100)
        ac.setText(self.progress_bar_volume, "volume")
        
        # - Speed label indicator
        self.speed_label = ac.addLabel(self.app_window, "Speed: 0 km/h")
        ac.setPosition(self.speed_label, 5, 155)
        ac.setFontSize(self.speed_label, 16)
        
        # - Speed progress bar indicator
        self.progress_bar_speed = ac.addProgressBar(self.app_window, "Speed level")
        ac.setPosition(self.progress_bar_speed, 130, 155)
        ac.setSize(self.progress_bar_speed, 150, 20)
        ac.setValue(self.progress_bar_speed, 0)
        ac.setText(self.progress_bar_speed, "speed")
        
        # - Config menu opening button
        self.config_btn = ac.addButton(self.app_window, "Config")
        ac.addOnClickedListener(self.config_btn, SpeedSensitiveVolume.config_btn_callback)
        ac.setSize(self.config_btn, 60, 25)
        ac.setFontAlignment(self.config_btn, "center")
        ac.setPosition(self.config_btn, 205, 100)
        
        # -- Min Volume control
        self.min_volume_label = ac.addLabel(self.app_window, "Min volume")
        ac.setPosition(self.min_volume_label, 5, 208)
        ac.setFontSize(self.min_volume_label, 16)
        self.config_menu_items.append(self.min_volume_label)
        
        self.min_volume_input = ac.addTextInput(self.app_window, "")
        ac.setSize(self.min_volume_input, 30, 20)
        ac.setPosition(self.min_volume_input, 130, 210)
        ac.setText(self.min_volume_input, str(self.min_volume))
        self.config_menu_items.append(self.min_volume_input)
        
        self.min_volume_input_unit = ac.addLabel(self.app_window, "%           (0, 100)")
        ac.setPosition(self.min_volume_input_unit, 165, 208)
        ac.setFontSize(self.min_volume_input_unit, 16)
        self.config_menu_items.append(self.min_volume_input_unit)
        
        # -- Max Volume control
        self.max_volume_label = ac.addLabel(self.app_window, "Max volume")
        ac.setPosition(self.max_volume_label, 5, 233)
        ac.setFontSize(self.max_volume_label, 16)
        self.config_menu_items.append(self.max_volume_label)
        
        self.max_volume_input = ac.addTextInput(self.app_window, "")
        ac.setSize(self.max_volume_input, 30, 20)
        ac.setPosition(self.max_volume_input, 130, 235)
        ac.setText(self.max_volume_input, str(self.max_volume))
        self.config_menu_items.append(self.max_volume_input)
        
        self.max_volume_input_unit = ac.addLabel(self.app_window, "%           (10, 100)")
        ac.setPosition(self.max_volume_input_unit, 165, 233)
        ac.setFontSize(self.max_volume_input_unit, 16)
        self.config_menu_items.append(self.max_volume_input_unit)
        
        # -- Min speed control
        self.min_speed_label = ac.addLabel(self.app_window, "Min speed")
        ac.setPosition(self.min_speed_label, 5, 258)
        ac.setFontSize(self.min_speed_label, 16)
        self.config_menu_items.append(self.min_speed_label)
        
        self.min_speed_input = ac.addTextInput(self.app_window, "")
        ac.setSize(self.min_speed_input, 30, 20)
        ac.setPosition(self.min_speed_input, 130, 260)
        ac.setText(self.min_speed_input, str(self.min_speed))
        self.config_menu_items.append(self.min_speed_input)
        
        self.min_speed_input_unit = ac.addLabel(self.app_window, "km/h     (30, 100)")
        ac.setPosition(self.min_speed_input_unit, 165, 258)
        ac.setFontSize(self.min_speed_input_unit, 16)
        self.config_menu_items.append(self.min_speed_input_unit)
        
        # -- Max speed control
        self.max_speed_label = ac.addLabel(self.app_window, "Max speed")
        ac.setPosition(self.max_speed_label, 5, 283)
        ac.setFontSize(self.max_speed_label, 16)
        self.config_menu_items.append(self.max_speed_label)
        
        self.max_speed_input = ac.addTextInput(self.app_window, "")
        ac.setSize(self.max_speed_input, 30, 20)
        ac.setPosition(self.max_speed_input, 130, 285)
        ac.setText(self.max_speed_input, str(self.max_speed))
        self.config_menu_items.append(self.max_speed_input)
        
        self.max_speed_input_unit = ac.addLabel(self.app_window, "km/h     (100, 300)")
        ac.setPosition(self.max_speed_input_unit, 165, 283)
        ac.setFontSize(self.max_speed_input_unit, 16)
        self.config_menu_items.append(self.max_speed_input_unit)
        
        # - Save for config
        self.save_btn = ac.addButton(self.app_window, "Save")
        ac.setPosition(self.save_btn, 5, 310)
        ac.setSize(self.save_btn, 50, 20)
        ac.addOnClickedListener(self.save_btn, SpeedSensitiveVolume.config_update_callback)
        self.config_menu_items.append(self.save_btn)
        
        self.reset_btn = ac.addButton(self.app_window, "Reset")
        ac.setPosition(self.reset_btn, 60, 310)
        ac.setSize(self.reset_btn, 60, 20)
        ac.addOnClickedListener(self.reset_btn, SpeedSensitiveVolume.config_reset_callback)
        self.config_menu_items.append(self.reset_btn)
        
        self.status_label = ac.addLabel(self.app_window, "")
        ac.setPosition(self.status_label, 5, 328)
        ac.setFontSize(self.status_label, 16)
        #ac.setText(self.status_label, "Configuration has been reset.")
        self.config_menu_items.append(self.status_label)
        
        for config_item in self.config_menu_items:
            ac.setVisible(config_item, 0)
        
        SpeedSensitiveVolume.scan_processes()

        return self.app_name

    def config_update_callback(*args):
        global config_update
        config_update = True

    def config_reset_callback(*args):
        global config_reset
        config_reset = True

    def enable_button_callback(*args):
        global enabled, enabled_changed
        enabled = not enabled
        enabled_changed = True

    def config_btn_callback(*args):
        global is_config_menu_opened, is_config_menu_opened_changed
        is_config_menu_opened = not is_config_menu_opened
        is_config_menu_opened_changed = True

    def update_status(self, text: str, color: int):
        Colors = {
            0: (1, 1, 1, 1), # White
            1: (0.8, 0, 0, 1), # Red
            2: (0, 0.8, 0, 1), # Green
        }
        ac.setText(self.status_label, text)
        ac.setFontColor(self.status_label, Colors[color][0], Colors[color][1], Colors[color][2], Colors[color][3])

    def acUpdate(self, deltaT):
        global new_scan, running_apps, enabled, enabled_changed, is_config_menu_opened, is_config_menu_opened_changed, width, height, config_update, config_reset
        if new_scan:
            new_scan = False
                
            # First remove old labels
            for app_label in self.apps_labels:
                ac.setText(app_label, "")
            self.apps_labels.clear()
            
            # Then add new labels
            lbl = ac.addLabel(self.app_window, " & ".join(running_apps))
            ac.setFontSize(lbl, 18)
            ac.setPosition(lbl, 15, 60)
            ac.setFontColor(lbl, 0, 0.8, 0, 1)
                
            self.apps_labels.append(lbl)
            self.update_status("Scanned new music apps", 2)
        elif enabled_changed:
            enabled_changed = False
            ac.setText(self.enable_button, "Disable" if enabled else "Enable")
            if enabled:
                ac.setFontColor(self.enable_button, 1, 1, 1, 1)
                self.update_status("Enabled plugin", 2)
            else:
                ac.setFontColor(self.enable_button, 1, 0, 0, 1)
                self.update_status("Disabled plugin", 1)         
        elif is_config_menu_opened_changed:
            is_config_menu_opened_changed = False
            if is_config_menu_opened:
                for config_item in self.config_menu_items:
                    ac.setVisible(config_item, 1)
                ac.setSize(self.app_window, width, height+170)
            else:
                for config_item in self.config_menu_items:
                    ac.setVisible(config_item, 0)
                ac.setSize(self.app_window, width, height)
        elif config_update:
            config_update = False
            if self.debug:
                ac.log("Updating config | Min vol: {0} | Max vol: {1} | Min speed: {2} | Max speed: {3}".format(self.min_volume, self.max_volume, self.min_speed, self.max_speed))
            
            try:
                self.min_volume = int(ac.getText(self.min_volume_input))
                self.max_volume = int(ac.getText(self.max_volume_input))
                self.min_speed = int(ac.getText(self.min_speed_input))
                self.max_speed = int(ac.getText(self.max_speed_input))
                self.config.set(option="min_volume", value=self.min_volume)
                self.config.set(option="max_volume", value=self.max_volume)
                self.config.set(option="min_speed", value=self.min_speed)
                self.config.set(option="max_speed", value=self.max_speed)
                self.update_status("Saved new config", 2)
            except:
                ac.log("An error occurred while saving, make sure to use only numbers !")
            
            if self.debug:
                ac.log("Updated config | Min vol: {0} | Max vol: {1} | Min speed: {2} | Max speed: {3}".format(self.min_volume, self.max_volume, self.min_speed, self.max_speed))
        elif config_reset:
            config_reset = False
            self.min_volume = 20
            self.max_volume = 100
            self.min_speed = 30
            self.max_speed = 100
            ac.setText(self.min_volume_input, str(self.min_volume))
            ac.setText(self.max_volume_input, str(self.max_volume))
            ac.setText(self.min_speed_input, str(self.min_speed))
            ac.setText(self.max_speed_input, str(self.max_speed))
            self.update_status("Config has been reset", 2)
        else:
            if enabled:
                if running_apps:
                    if (self.get_time() - self.last_time) >= self.scan_delay:
                        self.last_time = self.get_time()
                        current_speed = int(ac.getCarState(0, acsys.CS.SpeedKMH))
                        
                        ac.setText(self.speed_label, "Speed: {0} km/h".format(current_speed))
                        ac.setValue(self.progress_bar_speed, current_speed/self.max_speed)
                        volume = self.calculate_volume(current_speed)
                        if volume != self.last_volume:
                            for app in running_apps:
                                self.set_volume(app, volume)
                                self.last_volume = volume
                                ac.setValue(self.progress_bar_volume, volume/100)
                                ac.setText(self.volume_label, "Volume: {0}%".format(volume))

    def save_data(self, volume_linear, volume_expo, volume_log, volume_sigmoid, speed):
        if self.debug:
            self.debug_file.write("{0},{1},{2},{3},{4},{5}\n".format(volume_linear, volume_expo, volume_log, volume_sigmoid, speed, self.get_time()))

    def calculate_volume(self, speed):
        if speed <= self.min_speed:
            return self.min_volume
        if speed >= self.max_speed:
            return self.max_volume

        volume_range = float(self.max_volume - self.min_volume)
        
        """
            Here i leave some algorithms to calculate the volume, you can choose the one you like
            Make sure to change the <volume> variable at the end of the function
        """
        
        # Linear interpolation
        #volume_linear = int(self.min_volume + ((speed - self.min_speed) /  float(self.max_speed - self.min_speed)) * volume_range)
        
        # Exponential scaling
        volume_expo = int(self.min_volume + ((speed ** 2) / (self.max_speed ** 2)) * volume_range)
        
        # Logarihmic scaling
        #volume_log = int(self.min_volume + (math.log(speed + 1) / math.log(self.max_speed + 1)) * volume_range)
        
        # Sigmoid curve
        #volume_sigmoid = self.min_volume + (self.max_volume - self.min_volume) / (1 + math.exp(-1 * ((speed - self.min_speed) / (self.max_speed - self.min_speed) - 0.5)))
        
        volume = volume_expo
        
        if self.debug:
            ac.log("Volume will be set to: {0} | for speed : {1}".format(volume, speed))
            #self.save_data(volume_linear, volume_expo, volume_log, volume_sigmoid, speed)
        
        return volume
    
    def set_volume(self, app_name, level):
        try:
            if not os.path.exists(self.svv_path):
                return
                
            level = max(0, min(100, level))
            cmd = '"{0}" /SetVolume "{1}" {2}'.format(
                self.svv_path, 
                app_name, 
                str(level)
            )
            subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                shell=True
            )
        except Exception as e:
            ac.log("Volume error ({0}): {1}".format(app_name, str(e)))

volume_control = SpeedSensitiveVolume()

def acMain(ac_version):
    return volume_control.acMain(ac_version)

def acUpdate(deltaT):
    return volume_control.acUpdate(deltaT)