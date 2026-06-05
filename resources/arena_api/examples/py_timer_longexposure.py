# -----------------------------------------------------------------------------
# Copyright (c) 2024, Lucid Vision Labs, Inc.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# -----------------------------------------------------------------------------

import time
from arena_api.system import system
from arena_api.__future__.save import Writer

'''
Timer: Long Exposure
    This example introduces how the timer can be used to control specific features
    within the camera. In this case, we use the exposure as an example. Most cameras have a
    maxiumum exposure limit, but this provides the ability to bypass the exposure limit
    through the use of timer and trigger. First, the timer and trigger settings are configured 
    so that the timer is connected to the trigger, which is set to activate the exposure. As
    the timer begins, the trigger activates and the device starts to expose an image. Once 
    the timer duration expires, the exposure stops, the device grabs the image, and the image
    is saved to disk.
'''
TAB1 = "  "
TAB2 = "    "
TIMER_DURATION = 15000 # in milliseconds
FILE_NAME = 'Images/py_timer/image.jpg'


def create_devices_with_tries():
	'''
	Waits for the user to connect a device before
		raising an exception if it fails
	'''
	tries = 0
	tries_max = 6
	sleep_time_secs = 10
	devices = None
	while tries < tries_max:  # Wait for device for 60 seconds
		devices = system.create_device()
		if not devices:
			print(
				f'{TAB1}Try {tries+1} of {tries_max}: waiting for {sleep_time_secs} '
				f'secs for a device to be connected!')
			for sec_count in range(sleep_time_secs):
				time.sleep(1)
				print(f'{TAB1}{sec_count + 1 } seconds passed ',
					'.' * sec_count, end='\r')
			tries += 1
		else:
			return devices
	else:
		raise Exception(f'{TAB1}No device found! Please connect a device and run '
						f'the example again.')


def store_initial(nodemap):
	'''
	Stores intial node values, return their values at the end
	'''
	nodes = nodemap.get_node(['TriggerSelector', 'TriggerMode', 'TriggerSource', 
						   'TriggerActivation', 'TimerSelector', 'TimerTriggerSource', 
						   'TimerDuration', 'ExposureAuto', 'SoftwareSignalSelector'])

	trigger_selector_initial = nodes['TriggerSelector'].value
	trigger_mode_initial = nodes['TriggerMode'].value
	trigger_source_initial = nodes['TriggerSource'].value
	trigger_activation_initial = nodes['TriggerActivation'].value
	timer_selector_initial = nodes['TimerSelector'].value
	timer_trigger_source_initial = nodes['TimerTriggerSource'].value
	timer_duration_initial = nodes['TimerDuration'].value
	exposure_auto_initial = nodes['ExposureAuto'].value
	software_signal_selector_initial = nodes['SoftwareSignalSelector'].value

	initial_vals = [trigger_selector_initial, trigger_mode_initial, trigger_source_initial,
				 trigger_activation_initial, timer_selector_initial, timer_trigger_source_initial,
				 timer_duration_initial, exposure_auto_initial, software_signal_selector_initial]
	return nodes, initial_vals


def configure_timer(device, nodemap, nodes, initial_vals):
	'''
	demonstrates the use of timer to configure exposure time
	(1) configures the timer and trigger
	(2) starts stream
	(3) starts timer, which triggers the exposure
	(4) once timer duration is up, acquire image
	(5) save long exposure image to disk
	'''

	'''
	Setting required timer and trigger settings
		If any of these do not work, it may be due to the camera type
		or camera firmware. Try updating the firmware or using a
		different camera.
	'''

	"""
	Set trigger selector
		Set the trigger selector to Exposure Active. When triggered,
		the device will start exposing an image.
	"""
	print(f'{TAB1}Set trigger selector to Exposure Active')
	nodes['TriggerSelector'].value = 'ExposureActive'

	"""
	Set trigger source
		Set the trigger source to Timer 0 Active. This connects
		the trigger to the timer.
	"""
	print(f'{TAB1}Set trigger source to Timer 0 Active')
	nodes['TriggerSource'].value = 'Timer0Active'

	"""
	Set trigger activation
		Set the trigger source to Level High. This ensures
		that the trigger is activated when the timer is running.
	"""
	print(f'{TAB1}Set trigger activation to Level High')
	nodes['TriggerActivation'].value = 'LevelHigh'

	"""
	Set trigger mode
		Set trigger mode to on. This enables trigger mode
		on the camera.
	"""
	print(f'{TAB1}Set trigger mode to On')
	nodes['TriggerMode'].value = 'On'

	# set timer selector
	print(f'{TAB1}Set timer selector to Timer 0')
	nodes['TimerSelector'].value = 'Timer0'

	"""
	Set timer trigger source
		Set timer trigger source to Software Signal 0. Timer is only
		activated through software by calling the SoftwareSignal node.
	"""
	print(f'{TAB1}Set timer trigger source to Software Signal 0')
	nodes['TimerTriggerSource'].value = 'SoftwareSignal0'

	"""
	Set timer duration
		Set the timer duration to user-set duration. This gives user
		ability to control the duration of specific camera events
		without limitations. The timer duration node is configured 
		in microseconds.
	"""
	print(f'{TAB1}Set timer duration to {TIMER_DURATION} milliseconds')
	# convert TIMER_DURATION into microseconds
	timer_duration = float(TIMER_DURATION * 1000)
	nodes['TimerDuration'].value = timer_duration

	"""
	Set exposure auto
		Set exposure auto to off. Ensures the exposure time is only
		manipulated by user. Encapsulated in a try/catch block because
		some cameras do not have exposure auto.
	"""
	print(f'{TAB1}Set exposure auto to Off')
	try:
		nodes['ExposureAuto'].value = 'Off'
	except:
		print(f'{TAB2}Exposure auto not a feature available')

	"""
	Set software signal selector
		Set software signal selector to Software Signal 0. Connects software
		signal to timer trigger.
	"""
	print(f'{TAB1}Set software signal selector to Software Signal 0')
	nodes['SoftwareSignalSelector'].value = 'SoftwareSignal0'

	"""
	Setup stream values
	"""
	tl_stream_nodemap = device.tl_stream_nodemap
	tl_stream_nodemap['StreamAutoNegotiatePacketSize'].value = True
	tl_stream_nodemap['StreamPacketResendEnable'].value = True

	# start stream
	print(f'{TAB1}Start stream')
	device.start_stream()

	"""
	Trigger Armed
		Continually checks until trigger is armed. Once the trigger is
		armed, it is ready to be executed.
	"""
	print(f'{TAB2}Wait until trigger is armed')
	trigger_armed = False

	while trigger_armed is False:
		trigger_armed = bool(nodemap['TriggerArmed'].value)

	"""
	Start timer
		This is done through a software signal. This also triggers the 
		exposure active trigger, which starts to expose the image
	"""
	print(f'{TAB2}Start timer for {TIMER_DURATION / 1e3} seconds')
	nodemap['SoftwareSignalPulse'].execute()

	"""
	Acquire image
		This waits for the length of the timer duration to get an image.
	    If an image buffer is not ready by the timeout duration, it fails.
	    The result should be an image exposed to the duration of the timer.
	"""
	print(f'{TAB2}Get image')
	timeout = int(timer_duration)
	buffer = device.get_buffer(timeout=timeout)

	# save image
	writer = Writer.from_buffer(buffer)
	writer.pattern = FILE_NAME
	writer.save(buffer)
	print(f'{TAB2}Image saved {writer.saved_images[-1]}')

	# Requeue buffer
	device.requeue_buffer(buffer)

	# Stop stream
	print(f'{TAB1}Stop stream')
	device.stop_stream()

	"""
	Return nodes to their initial values
	"""
	nodes['TriggerSelector'].value = initial_vals[0]
	nodes['TriggerMode'].value = initial_vals[1]
	nodes['TriggerSource'].value = initial_vals[2]
	nodes['TriggerActivation'].value = initial_vals[3]
	nodes['TimerSelector'].value = initial_vals[4]
	nodes['TimerTriggerSource'].value = initial_vals[5]
	nodes['TimerDuration'].value = initial_vals[6]
	try:
		nodes['ExposureAuto'].value = initial_vals[7]
	except:
		print(f'{TAB1}Exposure auto feature not available')
	nodes['SoftwareSignalSelector'].value = initial_vals[8]


def example_entry_point():
	# Prepare example
	devices = create_devices_with_tries()
	device = system.select_device(devices)

	# Prepare initial node values
	nodemap = device.nodemap
	nodes, initial_vals = store_initial(nodemap)

	configure_timer(device, nodemap, nodes, initial_vals)

	# Destroy device
	system.destroy_device()
	print(f'{TAB1}Destroyed all created devices')



if __name__ == "__main__":
	print("Example Started\n")
	example_entry_point()
	print("\nExample Completed")
