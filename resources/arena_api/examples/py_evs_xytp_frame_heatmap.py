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

import ctypes
import time

from arena_api.system import system
from arena_api.buffer import BufferFactory
from arena_api.enums import PixelFormat
from arena_api.__future__.save import Writer

'''
XYTP Heatmap:
	This example demonstrates saving a BGR heatmap of a XYPT frame. It captures
	events as XYPT frame from EVS camera, interprets the XYPT data from the frame
	to retrieve the time value for each event pixel and then converts this data into
	a BGR buffer. The buffer is then used to create a jpg heatmap image.
'''

TAB1 = "  "
TAB2 = "    "
TAB3 = "	 "
RGB_MIN = 0
RGB_MAX = 255
IMAGE_TIMEOUT = 2000
JPG_FILE_NAME = "Images/Python_XYTP_Heatmap.jpg"

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

def create_bgr_heatmap_and_save(buffer, filepath):
	# XYTP frame buffer info
	# "LUCID_LucidXYTP128f" pixelformats have 4 channels pre pixel.
	#  Each channel is 32 bits float and they represent:
	#   - x position
	#   - y postion
	#   - t time 
	#   - p event 
	# the value can be dynamically calculated this way:
	#   int(buffer.bits_per_pixel/32) # 32 is the size of each channel
	LUCID_LucidXYTP128f_channels_per_pixel = xytp_frame_step_size = 4
	width, height = buffer.width, buffer.height
	num_pixels = width * height
 
	# Note that xytp buffer will only contain pixel with events
	# the number valid pixel size can be dynamically calculated this way:
	# 	int(buffer.size_filled / byte_per_pixle)
	bytes_per_pixle = buffer.bits_per_pixel / 8
	valid_event_size = int(buffer.size_filled / bytes_per_pixle)
	src_data = ctypes.cast(buffer.pdata, ctypes.POINTER(ctypes.c_float))
	print(f"{TAB2}Number of valid event pixel is: {valid_event_size}")

	# find minT and maxT for time channel (t)
	minT = float('inf')
	maxT = float('-inf')
	for i in range(valid_event_size):
		t = src_data[i * xytp_frame_step_size + 2]  # accessing the 't' time channel in XYTP
		minT = min(minT, t)
		maxT = max(maxT, t)
  
	# init output array
	BGR8_channels_per_pixel = bgr8_step_size = 3  # Blue, Green, Red
	array_BGR8_size_in_bytes = BGR8_channels_per_pixel * num_pixels
	CustomArrayType = (ctypes.c_byte * array_BGR8_size_in_bytes)
	dst_bgr8_array = CustomArrayType()
 
	# set color bound base on time value range
	range_t = maxT - minT
	yellow_border = minT + range_t / 4
	green_border = minT + range_t / 2
	cyan_border = minT + 3 * range_t / 4
	blue_border = maxT

	# assign colors based on the time (t) values
	for i in range(valid_event_size):
		x, y, t = src_data[i * xytp_frame_step_size], src_data[i * xytp_frame_step_size + 1], src_data[i * xytp_frame_step_size + 2]

		# color mapping logic based on time value
		if t <= yellow_border:
			percentage = (t - minT) / (yellow_border - minT)
			red = RGB_MAX
			green = int(RGB_MAX * percentage)
			blue = RGB_MIN
		elif t <= green_border:
			percentage = (t - yellow_border) / (green_border - yellow_border)
			red = int(RGB_MAX * (1 - percentage))
			green = RGB_MAX
			blue = RGB_MIN
		elif t <= cyan_border:
			percentage = (t - green_border) / (cyan_border - green_border)
			red = RGB_MIN
			green = RGB_MAX
			blue = int(RGB_MAX * percentage)
		elif t <= blue_border:
			percentage = (t - cyan_border) / (blue_border - cyan_border)
			red = RGB_MIN
			green = int(RGB_MAX * (1 - percentage))
			blue = RGB_MAX
		else:
			red = RGB_MIN
			green = RGB_MIN
			blue = RGB_MAX

		# calculate pixel offset in BGR format for JPG
		offset = int((int(y) * width + int(x)) * bgr8_step_size)
		dst_bgr8_array[offset] = blue
		dst_bgr8_array[offset + 1] = green
		dst_bgr8_array[offset + 2] = red
  
	# create and save the heatmap image
	print(f"{TAB2}Create BGR heatmap from XYPT Frame")
	buffer_bgr8 = BufferFactory.create(ctypes.cast(dst_bgr8_array, ctypes.POINTER(ctypes.c_ubyte)),
										array_BGR8_size_in_bytes, width, height, PixelFormat.BGR8)
	writer = Writer.from_buffer(buffer_bgr8)
	writer.save(buffer_bgr8, filepath)
	print(f'{TAB2}Save heatmap image as jpg to {writer.saved_images[-1]}')
	BufferFactory.destroy(buffer_bgr8)

'''
demonstrates saving evs heatmap image
	(1) sets acquisition mode
 	(2) sets buffer handling mode
 	(3) sets Event Format to EVS and camera event rate to 10 Mev/s
 	(4) sets EVS output format to XYTPFrame
 	(5) starts the stream
 	(6) acquires one image 
 	(7) collects time pixel channel for time range
 	(8) sets pixel color buffers based on time bound 
 	(9) writes jpg heatmap image using output buffer
 	(10) stops the stream
 	(11) requeues the buffer & cleans up
'''
def configure_and_capture_xytp_heatmap(device):
	
	nodemap = device.nodemap
	tl_stream_nodemap = device.tl_stream_nodemap
	nodes = device.nodemap.get_node(['Width', 'Height'])

	width = nodes['Width'].value
	height= nodes['Height'].value

	print(f'{TAB1}Image (w, h) = ({width} , {height})')

	# Set features before streaming -------------------------------------------
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

		# Set camera event rate to 10 Mev/s
		print(f'{TAB1}Set Camera Event Rate to 10 Mev/s')
		erc_enable_initial = nodemap.get_node('ErcEnable').value
		nodemap["ErcEnable"].value = True

		camera_event_rate_initial = nodemap.get_node('ErcRateLimit').value
		nodemap["ErcRateLimit"].value = 10.0

		# Set evs output format to XYTPFrame
		print(f'{TAB1}Set EVS output format to XYTPFrame')
		tl_stream_nodemap["StreamEvsOutputFormat"].value = "XYTPFrame"

		print(f'{TAB1}Start stream')
		device.start_stream(1)

		print(f'{TAB1}Get one image')
		buffer = device.get_buffer()

		if buffer.is_incomplete:
			print(f'{TAB3}Image {buffer.frame_id} is incomplete')
		else:
			create_bgr_heatmap_and_save(buffer,JPG_FILE_NAME)
			
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

	# Configure device and save images as jpg heatmap ----------------------------------------

	configure_and_capture_xytp_heatmap(device)

	# Clean up ----------------------------------------------------------------

	system.destroy_device()
	print(f'{TAB1}Destroyed all created devices')


if __name__ == '__main__':
	print('\nExample started\n')
	example_entry_point()
	print('\nExample finished successfully')
