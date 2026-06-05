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

from arena_api.__future__.save import Writer
from arena_api.enums import PixelFormat
from arena_api.system import system
from arena_api.buffer import BufferFactory
from arena_api.__future__.save import _xWriter

'''
Acquisition: Compressed Image Handling
	This example demonstrates how to acquire and process compressed image data
	from the camera using the Arena SDK. The example includes
	steps to configure the camera, acquire a compressed image, process the
	image to decompress it, and save both the raw input and decompressed images.
'''

TIMEOUT = 2000
TAB1 = "  "
TAB2 = "    "

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
	
def save_RAW_input_image(buffer):
	'''
	Takes compressed image data and saves the raw data
	'''
	print(f'{TAB2}Saving compressed image')

	# Set raw file save location
	filename = 'images\\py_acquisition_compressed_image_handling\\CompressedImage.raw'

	# Save function for .raw file
	_xWriter.SaveRawData(filename, buffer.compressed_image_pdata, buffer.size_filled)
	print(f'{TAB2}Image saved {filename}')

def process_and_save_decompressed_image(buffer):
	'''
	Decompresses compressed image and saves it as a file
	'''
	print(f'{TAB2}Decompressing to Mono8')

	# Decompress image
	converted_buffer = BufferFactory.decompress_image(buffer)

	# Get and print size for comparison
	decompressed_image_size = converted_buffer.size_filled
	print(f'{TAB2}Mono8 image size: {decompressed_image_size} bytes')

	# Save the decompressed image
	writer = Writer.from_buffer(converted_buffer)
	writer.pattern = 'images\\py_acquisition_compressed_image_handling\\DecompressedImage.png'
	writer.save(converted_buffer)
	print(f'{TAB2}Image saved {writer.saved_images[-1]}')

	# Destroy buffer to avoid memory leaks
	BufferFactory.destroy(converted_buffer)

def example_entry_point():
	'''
	This example demonstrates how to acquire and process compressed image data
	from the camera using the Arena SDK. The example includes
	steps to configure the camera, acquire a compressed image, process the
	image to decompress it, and save both the raw input and processed images.
	'''

	# Prepare example ------------------------------------------------------------
	
	# Create device
	devices = create_devices_with_tries()
	device = system.select_device(devices)

	# Run example ----------------------------------------------------------------

	# Get device nodemap
	nodemap = device.nodemap

	# Iterate through the PixelFormat enum and check for "QOI_Mono8"
	node = nodemap.get_node('PixelFormat')
	entries = node.enumentry_names
	found = False
	for e in entries:
		if (e == 'QOI_Mono8'):
			found = True
			break

	if (not found):
		print(f'{TAB1}QOI_Mono8 is not available in the PixelFormat enumeration for this camera.')
		return

	# Get initial node values in order to return their values at the end of the example
	pixel_format_initial = node.value

	# Set nodes ------------------------------------------------------------------
	# - PixelFormat to QOI_Mono8
	print(f'{TAB1}Settings nodes:')
	pixel_format_setting = 'QOI_Mono8'
	print(f'{TAB1}Setting pixel format to { pixel_format_setting }')
	node.value = pixel_format_setting

	# Get stream nodemap and alter settings
	tl_stream_nodemap = device.tl_stream_nodemap
	tl_stream_nodemap['StreamAutoNegotiatePacketSize'].value = True # enable stream auto negotiate packet size
	tl_stream_nodemap['StreamPacketResendEnable'].value = True # enable stream packet resend

	# Start stream
	with device.start_stream(1):

		print(f'{TAB1}Stream started with 1 buffer')
		
		# Get compressed image
		print(f'{TAB1}Get compressed image')
		buffer = device.get_buffer()

		# Get compressed image size
		compressed_image_size = buffer.size_filled
		print(f'{TAB2}QOI_Mono8 compressed image size: {compressed_image_size} bytes')

		save_RAW_input_image(buffer)

		process_and_save_decompressed_image(buffer)

		# Re-queue the image buffer
		device.requeue_buffer(buffer)

	# Stop stream
	print(f'{TAB1}Stop stream')
	device.stop_stream()
	
	# Return nodes to their initial values
	nodemap.get_node('PixelFormat').value = pixel_format_initial

	# Clean up example -----------------------------------------------------------

	# destroys all created devices
	system.destroy_device()
	print(f'{TAB1}Destroyed all created devices')


if __name__ == '__main__':
	print('\npy_aquisition_compressed_image_handling\n')
	print('\nExample started\n')
	example_entry_point()
	print('\nExample finished successfully\n')