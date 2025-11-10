import asyncio
from bleak import BleakScanner
import godice

class GoDiceManager:
    def __init__(self):
        self.dice = None                #Dice Object
        self.dice_connected = False     #Connection boolean
        self.battery_task = None        #Battery polling task
        self.dice_callback = None       #Callback for sending messages to Unity via Server

    # Connect dice to GoDiceManager
    async def connect_dice(self):
        # Scan nearby bluetooth devices, filter GoDice name devices and connect to closest one
        print("[GoDiceManager] Scanning for GoDice devices...")
        discovery_res = await BleakScanner.discover(timeout=5, return_adv=True)
        device_advdata_tuples = self._filter_godice_devices(discovery_res.values())

        if not device_advdata_tuples:
            print("[GoDiceManager] No GoDice devices found.")
            return {"success": False, "message": "No dice found"}

        device, _adv_data = self._select_closest_device(device_advdata_tuples)
        print(f"[GoDiceManager] Connecting to {device.name}...")

        # Establish connection to dice, pulse LEDs, start listening to rolls and create task for polling battery level
        try:
            self.dice = await godice.create(device.address, godice.Shell.D20).__aenter__()
            self.dice_connected = True

            asyncio.create_task(self.pulse_diceLED())
            #await self.dice.pulse_led(3, 100, 100, (0, 255, 0))
            await self.dice.subscribe_number_notification(self._handle_roll)

            self.battery_task = asyncio.create_task(self._poll_battery_level())
            print(f"[GoDiceManager] Connected to {device.name}")
            return {"success": True, "message": device.name}

        except Exception as e:
            print(f"[GoDiceManager] Connection error: {e}")
            return {"success": False, "message": str(e)}
    
    # Async pulse led function: to prevent blocking main thread
    async def pulse_diceLED(self):
        await self.dice.pulse_led(3, 100, 100, (0, 255, 0))

    # Disconnect the dice if any
    async def disconnect_dice(self):
        if self.dice == None:
            return
        self.dice_connected = False

        # Shutdown battery polling task
        if self.battery_task:
            self.battery_task.cancel()
            try:
                await self.battery_task
            except asyncio.CancelledError:
                pass
            self.battery_task = None

        # Disconnect the dice (unless it got disconnected on it's own)
        if self.dice:
            try:
                await self.dice.set_led((0, 0, 0), (0, 0, 0))
                await self.dice.disconnect()
                await self.dice.__aexit__(None, None, None)
                print("[GoDiceManager] Dice disconnected.")
            except Exception as e:
                print(f"[GoDiceManager] Error during disconnect: {e}")
            self.dice = None

        # Message Unity that dice disconnected
        self.dice_callback({"type": "disconnect",})

    # Poll for battery level & check if dice is still connected
    async def _poll_battery_level(self):
        try:
            while self.dice_connected:
                # Get battery level from dice
                try:
                    battery_lvl = await self.dice.get_battery_level()
                    print(f"[GoDiceManager] Battery level: {battery_lvl}")
                    await asyncio.sleep(10)
                # No polling result; expect that dice has disconnected; start disconnecting protocol
                except Exception as e:
                    print(f"[GoDiceManager] Battery polling error: {e}")
                    self.disconnect_dice()
                    break
        finally:
            print("[GoDiceManager] Battery polling stopped.")

    # Set callback function for GoDiceManager
    def set_dice_callback(self, callback):
        self.dice_callback = callback

    # Read connected dice's roll value and it to Unity
    async def _handle_roll(self, number, stability):
        print(f"Rolled: {number}, Stability: {stability}")
        if stability == godice.StabilityDescriptor.TILT_STABLE:
            if self.dice_callback:
                self.dice_callback({
                    "type": "roll",
                    "value": number
                })

    # Filter GoDice bluetooth devices
    def _filter_godice_devices(self, dev_advdata_tuples):
        return [
            (dev, adv_data)
            for dev, adv_data in dev_advdata_tuples
            if dev.name and dev.name.startswith("GoDice")
        ]

    # Select closest device from list
    def _select_closest_device(self, dev_advdata_tuples):
        return max(dev_advdata_tuples, key=lambda d: d[1].rssi)