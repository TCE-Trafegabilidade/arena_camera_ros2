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

from arena_api.system import system
from arena_api.__future__.save import Writer


'''
Save: EVS Save
    This example demonstrates how to acquire and save an image using the Event Stream (EVS) format.
    It covers setting up acquisition mode, configuring the camera for EVS,
    and saving the acquired image in the PLY format using the save library. 
'''
TAB1 = "  "
TAB2 = "    "
TAB3 = "	 "
FILE_NAME = "Images/Py_EVS_Save_Ply/Py_EVS_Save_Ply.ply"
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



def save_image(image_buffer, filepath):
	print(f'{TAB2}Prepare image parameters')
	width = image_buffer.width
	height = image_buffer.height
	bits_per_pixel = image_buffer.bits_per_pixel

	'''
	The buffer will be the size of the full image but we need to specify the number of 
	actual vertices stored in the buffer.
	'''
	size_filled = image_buffer.size_filled
	num_vertices = int(size_filled / (bits_per_pixel / 8))

	print(f'{TAB2}Prepare image writer')
	
	writer = Writer(width,height,bits_per_pixel, num_vertices)

	writer.save(image_buffer, filepath)
	print(f'{TAB1}Image saved {writer.saved_images[-1]}')


'''
demonstrates acquisition and save 
   (1) sets acquisition mode
   (2) sets buffer handling mode
   (3) sets Event Format to EVS and camera event rate to 10 Mev/s
   (4) sets EVS output format to XYTPFrame
   (5) starts the stream
   (6) acquires one image 
   (7) saves the image
   (8) requeues the buffer
   (9) stops the stream
'''
def configure_and_save_ply(device):

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

		# set evs output format to XYTPFrame
		print(f'{TAB1}Set EVS output format to XYTPFrame')
		tl_stream_nodemap["StreamEvsOutputFormat"].value = "XYTPFrame"

		print(f'{TAB1}Start stream')
		device.start_stream(1)

		print(f'{TAB1}Get one image')
		buffer = device.get_buffer()

		if buffer.is_incomplete:
			print(f'{TAB3}Image {buffer.frame_id} is incomplete')
		else:
			save_image(buffer,FILE_NAME)
			
		device.requeue_buffer(buffer)
		print(f'{TAB1}Image buffer requeued')
		
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

	# Configure device and save images as ply format ----------------------------------------

	configure_and_save_ply(device)

	# Clean up ----------------------------------------------------------------

	system.destroy_device()
	print(f'{TAB1}Destroyed all created devices')


if __name__ == '__main__':
	print('\nExample started\n')
	example_entry_point()
	print('\nExample finished successfully')
