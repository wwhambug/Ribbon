"""Advertise the official setup service for 12 seconds, without account pairing."""
import logging
import dbus
from gi.repository import GLib
from musegadget.ble_server import BleServer

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
server = BleServer(
    "MuseGadget000000",
    on_write=lambda packet: None,
    on_disconnect=lambda: None,
)
active = False

def check():
    global active
    bus = dbus.SystemBus()
    objects = dbus.Interface(bus.get_object('org.bluez', '/'),
                             'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
    for interfaces in objects.values():
        manager = interfaces.get('org.bluez.LEAdvertisingManager1', {})
        if int(manager.get('ActiveInstances', 0)) > 0:
            active = True
    print(f'ACTIVE_ADVERTISEMENT_VERIFIED={active}', flush=True)
    return False

def stop():
    server.stop()
    return False

GLib.timeout_add_seconds(12, stop)
GLib.timeout_add_seconds(3, check)
server.run()
if not active:
    raise SystemExit('No active BlueZ advertising instance was observed.')
