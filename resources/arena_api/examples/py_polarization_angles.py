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
import ctypes

from arena_api.buffer import BufferFactory
from arena_api.system import system
from arena_api.__future__.save import Writer
from arena_api.enums import PixelFormat

"""
Polarization, Angles
	This example introduces the basics of working with the polarized
	angles pixel format. Specifically, this example retrieves a 4-channel
	PolarizedAngles_0d_45d_90d_135d_Mono8 or PolarizedAngles_0d_45d_90d_135d_BayerRG8,
	depending on the camera. It first splits the 4 channels into separate images. Then,
	it writes the four images onto a 2x2 grid and saves it to disk. Finally, it saves
	each individual image to disk.
"""
TAB1 = "  "
TAB2 = "    "
TAB3 = "      "

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
      
def write_to_2x2_grid(img, dst, dst_offset, dst_step, dst_half_stride):
	"""
	Helper function to write an individual image to a location
		within a 2x2 grid
	"""
	src = img.data
	src_h = img.height
	src_w = img.width
	src_step = PixelFormat.get_bits_per_pixel(img.pixel_format) // 8

	src_index = 0
	dst_index = int(dst_offset)

	for i in range(src_h):
		for j in range(src_w):
			dst[dst_index] = src[src_index]
			src_index += int(src_step)
			dst_index += int(dst_step)
		dst_index += int(dst_half_stride)

def save_image(img, filename):
	"""
	Helper function that takes an image and saves
		it to a given path in disk
	"""
	writer_jpg = Writer.from_buffer(img)
            
	writer_jpg.save(img, filename)
	
	print(f'{TAB3}Save image to {writer_jpg.saved_images[-1]}')

def example_entry_point():
	"""
	Demonstrates acquisition and processing of polarized angles image data:
	 (1) configures camera to appropriate supported pixel format
	 (2) acquires a polarized input image
	 (3) splits the polarized input image into 4 separate images
	 (4) saves images into a 2x2 grid image
	 (5) saves the 4 separate images to disk
	"""

	# Create a device
	devices = create_devices_with_tries()
	device = system.select_device(devices)
      
	# Get device stream nodemap
	tl_stream_nodemap = device.tl_stream_nodemap

	# Enable stream auto negotiate packet size
	tl_stream_nodemap['StreamAutoNegotiatePacketSize'].value = True

	# Enable stream packet resend
	tl_stream_nodemap['StreamPacketResendEnable'].value = True
  
	# Get nodes ---------------------------------------------------------------
	nodes = device.nodemap.get_node(['PixelFormat'])

	# Retrieve enumeration entries and check which polarized angles pixel format is supported
	pixel_format = '';
	for pixel_format_name in nodes['PixelFormat'].enumentry_names:
		if (pixel_format_name == 'PolarizedAngles_0d_45d_90d_135d_BayerRG8'):
			pixel_format = pixel_format_name
		elif (pixel_format_name == 'PolarizedAngles_0d_45d_90d_135d_Mono8'):
			pixel_format = pixel_format_name

	if pixel_format == '':
		print("\tError - This example requires PolarizedAngles_0d_45d_90d_135d_* pixel formats")
		return

	# Get node values that will be changed in order to return their values at
	# the end of the example
	pixel_format_initial_value = nodes['PixelFormat'].value

	# Change pixel format to either:
	#    (1) PolarizedAngles_0d_45d_90d_135d_BayerRG8 (color)
	#	 (2) PolarizedAngles_0d_45d_90d_135d_Mono8 (monochrome)
	#    These pixel formats have 4-channels, each containing data from
	#    each degree of polarization (0, 45, 90, and 135). These channels
	#    are allocated in memory side-by-side.
	print(f'{TAB1}Setting Pixel Format to {pixel_format}')
	nodes['PixelFormat'].value = pixel_format

	# Grab and save an image buffer -------------------------------------------
	print(f'{TAB1}Starting stream')
	with device.start_stream(1):
		print(f'{TAB2}Acquire image')
		image_buffer = device.get_buffer()
        
		# src info
		src_width = image_buffer.width         
		src_height = image_buffer.height
		src_pixel_format = image_buffer.pixel_format

		if src_pixel_format != PixelFormat.PolarizedAngles_0d_45d_90d_135d_BayerRG8 and src_pixel_format != PixelFormat.PolarizedAngles_0d_45d_90d_135d_Mono8:
			print("\tError - Input image pixel format [{}] is a non-polarized format".format(src_pixel_format))
			return

		# 2x2 info
		dst_2x2_width = src_width * 2
		dst_2x2_height = src_height * 2
		dst_2x2_pixel_format = PixelFormat.BayerRG8 if src_pixel_format == PixelFormat.PolarizedAngles_0d_45d_90d_135d_BayerRG8 else PixelFormat.Mono8
		dst_2x2_step = PixelFormat.get_bits_per_pixel(dst_2x2_pixel_format) // 8

		dst_2x2_stride = dst_2x2_width * dst_2x2_step
		dst_2x2_data_size = dst_2x2_width * dst_2x2_height * dst_2x2_step

		# Allocate space for 2x2 grid
		dst_data = (ctypes.c_ubyte * dst_2x2_data_size)()

		# Reference set up to starting position of each quadrant of
		# destination 2x2 grid to write to
		dst_top_left = 0;
		dst_top_right = dst_top_left + (dst_2x2_stride / 2)
		dst_bottom_left = dst_top_left + (dst_2x2_data_size / 2)
		dst_bottom_right = dst_top_left + (dst_2x2_data_size / 2) + (dst_2x2_stride / 2)

		# Splits the polarized image into 4 images:
		#    This function separates the four channels of the
		#    polarized pixel format and returns an array of
		#    pointers to the separated images.
		print(f'{TAB2}Splitting 4-channel pixel format into array of images')
		polarized_images = BufferFactory.split_channels(image_buffer)

		# Write separate images to a 2x2 grid
		#    Given a buffer with enough allocated space for
		#    four images, this writes the data of each image
		#    into its respective location within the 2x2 grid.
		print(f'{TAB2}Writing image buffers to a 2x2 grid')

		starting_positions = [dst_top_left, dst_top_right, dst_bottom_left, dst_bottom_right]
		for i in range(len(polarized_images)):
			# Grab image from array of polarized images
			img = polarized_images[i]

			# Write image to 2x2 grid
			write_to_2x2_grid(img, dst_data, starting_positions[i], dst_2x2_step, dst_2x2_stride / 2)
        
		uint8_ptr = ctypes.POINTER(ctypes.c_ubyte)
		dst_data_ptr = ctypes.cast(dst_data, uint8_ptr)
            
		# Save the 2x2
		create_buffer = BufferFactory.create(dst_data_ptr, dst_2x2_data_size, dst_2x2_width, dst_2x2_height, dst_2x2_pixel_format)
		output_buffer = BufferFactory.convert(create_buffer, PixelFormat.BGR8 if src_pixel_format == PixelFormat.PolarizedAngles_0d_45d_90d_135d_BayerRG8 else PixelFormat.Mono8)
        
		writer_jpg = Writer.from_buffer(output_buffer)
            
		writer_jpg.save(output_buffer, 'images/py_polarization_angles/polarized_2x2_tile.jpg')
		
		print(f'{TAB2}Save 2x2 image to {writer_jpg.saved_images[-1]}')

		# Saves each image to disk
		#    Converts each of the images into a
		#    displayable format and saves the image as a JPEG
		print(f'{TAB2}Saving each image to disk')

		degrees = ['0', '45', '90', '135']
		for i in range(len(polarized_images)):
			# Convert image to displayable format
			img = polarized_images[i]
			convert_buffer = BufferFactory.convert(img, PixelFormat.BGR8 if src_pixel_format == PixelFormat.PolarizedAngles_0d_45d_90d_135d_BayerRG8 else PixelFormat.Mono8)

			# Save image
			save_image(convert_buffer, 'images/py_polarization_angles/polarized_' + degrees[i] + '.jpg')

			# Clean up
			BufferFactory.destroy(convert_buffer)
        
		# Clean up
		BufferFactory.destroy(output_buffer)
		BufferFactory.destroy(create_buffer)
      
		device.requeue_buffer(image_buffer)
		
		device.stop_stream()
		print(f'{TAB1}Stream stopped')
	
	# Reset the pixel format to its initial value
	nodes['PixelFormat'].value = pixel_format_initial_value
      
	system.destroy_device()
	print(f'{TAB1}Destroyed all created devices')

if __name__ == '__main__':
	print('\nWARNING:\nTHIS EXAMPLE MIGHT CHANGE THE DEVICE(S) SETTINGS!')
	print('\nExample started\n')
	example_entry_point()
	print('\nExample finished successfully')
