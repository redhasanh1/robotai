# ESP32 USB drivers

The ESP32 talks to the laptop through a USB-to-serial chip on the board. Windows 11 usually installs the driver
by itself the first time you plug the board in. Only do this page if **no new COM port appears**.

## 1. Which chip is on your board?

Look at the small chip next to the USB socket, or plug the board in and open **Device Manager → Ports (COM & LPT)**
(or "Other devices" if the driver is missing):

| You see | Chip | Driver |
|---|---|---|
| "USB-SERIAL CH340 (COM5)" or a chip marked CH340 / CH343 | WCH CH340 | https://www.wch-ic.com/downloads/CH341SER_EXE.html |
| "Silicon Labs CP210x USB to UART Bridge (COM5)" | Silabs CP2102 | https://www.silabs.com/developer-tools/usb-to-uart-bridge-vcp-drivers (CP210x Universal Windows Driver) |
| "USB Serial Device (COM5)" | built-in USB (ESP32-S3 etc.) | none needed |

Freenove ESP32 boards normally use the **CH340**. Download from the official vendor page only, run the installer,
unplug and replug the board.

## 2. Nothing shows up at all?

- Swap the USB cable. Many cables are **charge-only** (no data wires) - this is the #1 problem.
- Try another USB port (not through a hub).
- The board's red power LED should be on.

## 3. Upload stuck at "Connecting....."

Hold the **BOOT** button on the ESP32 until the percentage starts climbing, then let go.
After uploading, press **EN** (reset) once.
