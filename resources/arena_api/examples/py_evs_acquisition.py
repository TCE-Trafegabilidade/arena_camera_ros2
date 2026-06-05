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

# -----------------------------------------------------------------------------
# Warning:
#
# EVS examples support only on windows at the moment
# -----------------------------------------------------------------------------

import time
import locale

from arena_api.system import system
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

'''
Acquisition: EVS
    This example demonstrates how to acquire images using the EVS
    (Electronic Viewfinder System) stream protocol, which is designed 
    to provide efficient and high-quality image transfer from the camera 
    to the host system.
'''
TAB1 = "  "
TAB2 = "    "
TAB3 = "	 "
'''
=-=-=-=-=-=-=-=-=-
=-=- EXAMPLE =-=-
=-=-=-=-=-=-=-=-=-
'''

def create_devices_with_tries():
	'''
	This function waits for the user to connect a device before raising
		an exception
	'''

	tries = 0
	tries_max = 6
	sleep_time_secs = 10
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
			print(f'{TAB1}Created {len(devices)} device(s)')
			return devices
	else:
		raise Exception(f'{TAB1}No device found! Please connect a device and run '
						f'the example again.')


def get_evs_event_rate(rate):
    if rate < 1000:
        return f"{rate:.0f} ev/s"
    elif rate < 1000 * 1000:
        return f"{(rate / 1000):.1f} Kev/s"
    elif rate < 1000 * 1000 * 1000:
        return f"{(rate / (1000 * 1000)):.1f} Mev/s"
    else:
        return f"{(rate / (1000 * 1000 * 1000)):.1f} Gev/s"


def get_evs_gvsp_frame_rate(rate):
    return f"{rate:.0f} Bid/s"


def get_evs_link_throughput(rate):
    if rate < 1000:
        return f"{rate:.0f} Bps"
    elif rate < 1000 * 1000:
        return f"{(rate / 1000):.1f} KBps"
    elif rate < 1000 * 1000 * 1000:
        return f"{(rate / (1000 * 1000)):.1f} MBps"
    else:
        return f"{(rate / (1000 * 1000 * 1000)):.1f} GBps"

'''
demonstrates evs acquisition
    (1) sets acquisition mode
    (2) sets buffer handling mode
    (3) sets Event Format to EVS and camera event rate to 10 Mev/s
    (4) sets EVS output format to CDFrame
    (5) sets EVS accumulation time to auto
    (6) starts the stream
    (7) gets a number of images
    (8) prints information from images
    (9) requeues buffers
    (10) stops the stream
'''
def configure_and_get_image_buffers(device):

	nodemap = device.nodemap
	tl_stream_nodemap = device.tl_stream_nodemap
	nodes = device.nodemap.get_node(['Width', 'Height'])

	width = nodes['Width'].value
	height= nodes['Height'].value

	print(f'{TAB1}Image (w, h) = ({width} , {height} )')

	# Set features before streaming.-------------------------------------------
	print(f'{TAB1}Set acquisition mode to \'Continuous\'')

	initial_acquisition_mode = nodemap.get_node("AcquisitionMode").value

	nodemap.get_node("AcquisitionMode").value = "Continuous"

	print(f'{TAB1}Set buffer handling mode to \'NewestOnly\'')
	
	tl_stream_nodemap["StreamBufferHandlingMode"].value = "NewestOnly"

	'''
	The EventFormat node determines whether the camera can use the EVS datastream engine. 
		When set to EVS, Arena switches to the EVS engine. If EVS is not supported, 
		the acquisition mode is restored to its original setting, and the process is exited.
	'''

	try:
		event_format_initial = nodemap.get_node('EventFormat').value

		print(f'{TAB1}Set Event Format to EVT3.0')
		nodemap["EventFormat"].value = "EVT3_0"

		# set camera event rate to 10 Mev/s
		print(f'{TAB1}Set Camera Event Rate to 10 Mev/s')
		erc_enable_initial = nodemap.get_node('ErcEnable').value
		nodemap["ErcEnable"].value = True

		camera_event_rate_initial = nodemap.get_node('ErcRateLimit').value
		nodemap["ErcRateLimit"].value = 10.0

		# set evs output format to CDFram
		print(f'{TAB1}Set EVS output format to CDFrame')
		tl_stream_nodemap["StreamEvsOutputFormat"].value = "CDFrame"

		# set evs accumulation time to auto
		print(f'{TAB1}Set EVS Accumulation Time to auto')
		stream_frame_generator_fps = tl_stream_nodemap["StreamFrameGeneratorFPS"].value
		tl_stream_nodemap["StreamFrameGeneratorAccumTime"].value = int (1000000 / stream_frame_generator_fps)

		number_of_buffers = 25

		device.start_stream(number_of_buffers)
		print(f'{TAB1}Stream started with {number_of_buffers} buffers')

		print(f'{TAB1}Get {number_of_buffers} buffers in a list')
		buffers = device.get_buffer(number_of_buffers)

		for count, buffer in enumerate(buffers):
			print(f'{TAB2}buffer {count:{2}} received')

			if buffer.is_incomplete:
				print(f'{TAB3}Image {buffer.frame_id} is incomplete')

			event_rate = tl_stream_nodemap["StreamEvsEventRate"].value
			print(f'{TAB3}Event Rate: {get_evs_event_rate(event_rate)}')

			gvsp_frame_rate = tl_stream_nodemap["StreamEvsGvspFrameRate"].value
			print(f'{TAB3}GVSP Frame Rate: {get_evs_gvsp_frame_rate(gvsp_frame_rate)}')

			link_throughput = tl_stream_nodemap["StreamEvsLinkThroughput"].value
			print(f'{TAB3}GVSP Frame Rate: {get_evs_link_throughput(link_throughput)}')

		device.requeue_buffer(buffers)
		print(f'{TAB1}Requeued {number_of_buffers} buffers')

		device.stop_stream()
		print(f'{TAB1}Stream stopped')

		# Restore initial values
		nodemap.get_node("ErcEnable").value = erc_enable_initial
		nodemap.get_node("ErcRateLimit").value = camera_event_rate_initial
		nodemap.get_node("EventFormat").value = event_format_initial

	except:
		print(f'{TAB1}Connected camera does not support any EventFormats\n')

	# Restore initial values
	nodemap.get_node("AcquisitionMode").value = initial_acquisition_mode


def example_entry_point():

	# Get connected devices ---------------------------------------------------

	# Create a device
	devices = create_devices_with_tries()
	device = system.select_device(devices)

	# Configure device and grab images ----------------------------------------

	configure_and_get_image_buffers(device)

	# Clean up ----------------------------------------------------------------

	system.destroy_device()
	print(f'{TAB1}Destroyed all created devices')


if __name__ == '__main__':
	print('\nExample started\n')
	example_entry_point()
	print('\nExample finished successfully')
