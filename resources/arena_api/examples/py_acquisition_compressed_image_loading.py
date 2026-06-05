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

import os
import time

from arena_api.__future__.save import Writer
from arena_api.enums import PixelFormat
from arena_api.system import system
from arena_api.buffer import BufferFactory
from arena_api.__future__.save import _xWriter, _xReader

'''
Acquisition: Compressed Image Loading
	This example demonstrates how to handle compressed image data, specifically
	loading and processing from raw data files using the Arena SDK. The example
	includes steps to configure the camera, acquire a compressed image, save
	the raw file, load the raw file, decompress the data, and save the decompressed
	image.
'''

TIMEOUT = 2000
TAB1 = "  "
TAB2 = "    "

RAW_FILE_PATH = "images\\py_acquisition_compressed_image_loading\\CompressedImage"
PNG_FILE_PATH = "images\\py_acquisition_compressed_image_loading\\DecompressedImage"

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
	
def save_compressed_image(buffer, index):

	print(f'{TAB2}Save compressed input image data to', end=' ')

	filename = RAW_FILE_PATH + str(index) + ".raw"

	# Save function for .raw file
	_xWriter.SaveRawData(filename, buffer.compressed_image_pdata, buffer.size_filled)
	print(f'{filename}')

def load_and_process_raw_image(in_file, out_file):
	'''
	Demonstrates loading and processing of compressed image data.
		(1) Loads raw image
		(2) Decompresses raw image
		(3) Saves decompressed image into readable format
	'''
	print(f'{TAB1}Load and process image')

	begin = time.time()

	for i in range(0, 10):
		
		in_filename = in_file + str(i) + ".raw"

		# Read raw file size
		size = os.path.getsize(in_filename);

		# Read file
		pdata = _xReader.LoadRawData(in_filename, size)

		# Load file into compressed image
		compressed_image = BufferFactory.create_compressed_image(pdata, size, PixelFormat.QOI_Mono8)

		# Decompress image
		decompressed_image = BufferFactory.decompress_image(compressed_image)

		# Get and print size for comparison
		decompressed_image_size = decompressed_image.size_filled
		print(f'{TAB2}Decompressed image {i} size: {decompressed_image_size} bytes')

		out_filename = out_file + str(i) + ".png"

		# Save the decompressed image
		writer = Writer.from_buffer(decompressed_image)
		writer.pattern = out_filename
		writer.save(decompressed_image)
		print(f'{TAB2}Image saved {writer.saved_images[-1]}')

		# Destroy buffer to avoid memory leaks
		BufferFactory.destroy(decompressed_image)
		BufferFactory.destroy_compressed_image(compressed_image)

	end = time.time()
	print(f'{TAB1}Time to decompress 10 images (sec) = {end - begin}')

def acquire_and_save_raw_image(device):
	'''
	Demonstrates acquisition and saving of compressed image data.
		(1) Configures the camera to use a compressed pixel format
		(2) Acquires a compressed input image
		(3) Saves the raw input image
	'''
	print(f'{TAB1}Acquire and save compressed image')

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

		for i in range(0, 10):
			# Get compressed image
			print(f'{TAB2}Get compressed image {i}')
			buffer = device.get_buffer()

			# Get compressed image size
			compressed_image_size = buffer.size_filled
			print(f'{TAB2}Compressed image {i} size: {compressed_image_size} bytes')

			# Save the raw image
			save_compressed_image(buffer, i)

			# Re-queue the image buffer
			device.requeue_buffer(buffer)

	# Stop stream
	print(f'{TAB1}Stop stream')
	device.stop_stream()
	
	# Return nodes to their initial values
	nodemap.get_node('PixelFormat').value = pixel_format_initial

def example_entry_point():
	'''
	This example demonstrates how to handle compressed image data, specifically
	loading and processing from raw data files using the Arena SDK. The example
	includes steps to configure the camera, acquire a compressed image, save
	the raw file, load the raw file, decompress the data, and save the decompressed
	image.
	'''

	# Prepare example ------------------------------------------------------------
	
	# Create device
	devices = create_devices_with_tries()
	device = system.select_device(devices)

	# Run example ----------------------------------------------------------------

	acquire_and_save_raw_image(device)
	load_and_process_raw_image(RAW_FILE_PATH, PNG_FILE_PATH)

	# Clean up example -----------------------------------------------------------

	# destroys all created devices
	system.destroy_device()
	print(f'{TAB1}Destroyed all created devices')


if __name__ == '__main__':
	print('\npy_aquisition_compressed_image_loading\n')
	print('\nExample started\n')
	example_entry_point()
	print('\nExample finished successfully\n')