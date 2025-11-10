import sys
import asyncio
import requests
from bleak import BleakScanner
import godice
from PyQt6.QtWidgets import QApplication, QMainWindow
from DiceWindow import Ui_MainWindow
from qasync import QEventLoop, asyncSlot

apiurl = "YOUR-SUBMITROLLRESULT HTTP GATEWAY URL+ROUTE"

class MainWindow(QMainWindow):
    # Init for window
    def __init__(self):
        super().__init__()
        self.readyPlayer = False
        self.sendingRoll = False

        self.diceConnected = False
        self.diceTask = None
        
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setFixedSize(650, 400)

        self.ui.readyButton.setCheckable(True)
        self.ui.readyButton.setChecked(False)

        self.ui.readyButton.clicked.connect(self.readyPlayerName)
        self.ui.connectButton.clicked.connect(self.on_button_click)

    # Ready up for sending data to AWS with typed name
    def readyPlayerName(self, checked):
        length = len(window.ui.playernameLine.text())
        if length < 3:
            print("PlayerID too short! (3 Mininum)")
            self.ui.readyButton.setChecked(False)
            return
        
        self.readyPlayer = checked
        if checked == True:
            self.ui.readyButton.setText("Unready")
            self.ui.readyButton.setChecked(True)
        else:
            self.ui.readyButton.setText("Ready")
            self.ui.readyButton.setChecked(False)
        self.ui.playernameLine.setEnabled(not checked)

    # Connect to nearest dice with button / disconnect connected dice
    @asyncSlot()
    async def on_button_click(self):
        self.ui.connectButton.setEnabled(False)
        if self.diceConnected:
            self.diceConnected = False
        else:
            await self.run_godice_logic()

    # Connect to GoDice and start listening to die
    async def run_godice_logic(self):
        self.ui.diceBox.setTitle("Discovering GoDice devices...")
        discovery_res = await BleakScanner.discover(timeout=5, return_adv=True)
        device_advdata_tuples = filter_godice_devices(discovery_res.values())

        if not device_advdata_tuples:
            self.ui.diceBox.setTitle("No GoDice devices found.")
            self.ui.connectButton.setEnabled(True)
            return

        print_device_info(device_advdata_tuples)
        self.ui.diceBox.setTitle("Connecting to GoDice...")
        device, _adv_data = select_closest_device(device_advdata_tuples)

        try:
            async with godice.create(device.address, godice.Shell.D20) as dice:
                self.diceConnected = True
                self.ui.connectButton.setText("Disconnect")
                self.ui.connectButton.setEnabled(True)
                self.ui.diceBox.setTitle(f"{device.name}")

                # Pulse LEDs on the connected dice
                await dice.pulse_led(5, 100, 100, (0, 255, 0))

                # Subcribe to dice notifications and check battery level every 10 seconds
                self.diceTask = asyncio.create_task(self.poll_battery_level(dice))
                await dice.subscribe_number_notification(lambda number, desc: notification_callback(number, desc, self))

                # Keep the connection loop running 
                while self.diceConnected:
                    await asyncio.sleep(1)

                await self.cleanup_connection(dice)

        except Exception as e:
            print(f"Connection lost or error occurred: {e}")
            self.ui.diceBox.setTitle("Dice Connection lost!")
            await self.cleanup_connection(dice)

    # Get battery level of connected dice
    async def poll_battery_level(self, dice):
        try:
            while self.diceConnected:
                try:
                    battery_lvl = await dice.get_battery_level()
                    self.ui.batteryLabel.setText(f"Battery level: {battery_lvl}")
                    await asyncio.sleep(10)
                except Exception as e:
                    print(f"Battery polling error: {e}")
                    self.diceConnected = False
                    break
        finally:
            print(f"Battery polling ended, disconnected dice.")

    # Cleanup dice disconnection
    async def cleanup_connection(self, dice):
        # Cancel battery polling task properly
        if self.diceTask:
            self.diceTask.cancel()
            try:
                await self.diceTask
            except asyncio.CancelledError:
                pass
            self.diceTask = None

        # Discconect dice (unless it got disconnected for other reasons)
        if dice:
            try:
                await dice.set_led((0, 0, 0), (0, 0, 0))
                await dice.disconnect()
                print("Byez noppa.")
            except Exception as e:
                print(f"Error during disconnect: {e}")

        # Clear dice data labels
        self.ui.batteryLabel.setText("")
        self.ui.rollLabel.setText("")
        self.ui.stabilityLabel.setText("")
        self.ui.responseLabel.setText("")

        # Reset connect button
        self.ui.connectButton.setText("Connect")
        self.ui.connectButton.setEnabled(True)
        self.ui.diceBox.setTitle("GoDice Disconnected.")
        
# Get roll data and possibly send it to AWS
async def notification_callback(number, stability_descr, main_window: MainWindow):
    # Print roll data on Application
    print(f"Number: {number}, stability descriptor: {stability_descr}")
    main_window.ui.rollLabel.setText(f"Roll result: {number}")
    main_window.ui.stabilityLabel.setText(f"Die State: {stability_descr}")

    # Send roll value to AWS if proper roll & playerID is set ready
    if stability_descr == godice.StabilityDescriptor.TILT_STABLE:
        if main_window.readyPlayer == True and window.sendingRoll == False:
            main_window.sendingRoll = True
            print(f"Sending roll value {number} to AWS for player {main_window.ui.playernameLine.text()}")
            payload = {
                'playerID': f"{main_window.ui.playernameLine.text()}",
                'value': f"{number}"
            }
            headers = {'Content-Type': 'application/json'}

            # Print received response from AWS
            response = requests.post(apiurl, json=payload, headers=headers)
            main_window.ui.responseLabel.setText(f"Response code {response.status_code}: {response.json()}")
            print(response.status_code, response.json())
            main_window.sendingRoll = False
        else:
            print("Not readied up! No data sent to AWS.")
    else:
        print("Not stable roll!")

# Filter bluetooth devices to only GoDices    
def filter_godice_devices(dev_advdata_tuples):
    return [
        (dev, adv_data)
        for dev, adv_data in dev_advdata_tuples
        if (dev.name and dev.name.startswith("GoDice"))
    ]

# Select closest GoDice device
def select_closest_device(dev_advdata_tuples):
    def _rssi_as_key(dev_advdata):
        _, adv_data = dev_advdata
        return adv_data.rssi

    return max(dev_advdata_tuples, key=_rssi_as_key)

# Print device information
def print_device_info(devices):
    for dev, adv_data in devices:
        print(f"Name: {dev.name}, address: {dev.address}, rssi: {adv_data.rssi}")

# Keep window script running forever until manually closed
if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.show()

    with loop:
        loop.run_forever()

# Start venv: "venv\Scripts\activate"
# Start script: "python app.py"
# Convert UI to python: "pyuic6 DiceWindow.ui -o DiceWindow.py"
# Async PyQt6 bridge: "pip install qasync"