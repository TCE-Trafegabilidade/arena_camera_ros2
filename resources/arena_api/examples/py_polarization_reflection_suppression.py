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
import math

from arena_api.buffer import BufferFactory
from arena_api.system import system
from arena_api.__future__ import save
from arena_api.__future__.save import Writer
from arena_api.enums import PixelFormat

"""
Polarization: Reflection Suppression
    This example demonstrates the process of suppressing reflections in
    image data acquired from a polarized sensor camera (polar-color)
"""
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

def save(buffer):
    
	writer = Writer()
	writer.pattern = 'images/py_polarization/input_image.raw'

	# Save converted buffer
	writer.save(buffer)
	print(f'{TAB2}Save input image to {writer.saved_images[-1]}')
      
def suppress_reflection(src_data, src_step, dst_data, dst_step, dst_size):
    src_length = len(src_data)
    
    for i in range(dst_size):
        p0_index = i * src_step
        p45_index = p0_index + 1
        p90_index = p0_index + 2
        p135_index = p0_index + 3

        if p135_index >= src_length:
            break

        _90 = float(src_data[p90_index])
        _45 = float(src_data[p45_index])
        _135 = float(src_data[p135_index])
        _0 = float(src_data[p0_index])

        theta = 0.5 * math.atan2(_45 - _135, _0 - _90) + math.pi / 2.0
        sintheta = math.sin(2.0 * theta) * 0.5
        costheta = math.cos(2.0 * theta) * 0.5

        _signed = (0.25 * (_0 + _45 + _90 + _135)) + (costheta * (_0 - _90)) + (sintheta * (_45 - _135))

        if _signed > 255.0:
            _signed = 255.0

        dst_value = max(0, int(_signed))

        dst_index = i * dst_step
        if dst_index + 2 < len(dst_data):
            dst_data[dst_index] = dst_value
            dst_data[dst_index + 1] = dst_value
            dst_data[dst_index + 2] = dst_value

def example_entry_point():
	"""
	Demonstrates acquisition and processing of polarized image data to suppress reflections:
	 (1) configures the camera to a polarized pixel format
	 (2) acquires a polarized input image
	 (3) processes the raw input image to suppress reflections
	 (4) saves the processed image to disk
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
	nodes = device.nodemap.get_node(['Width', 'Height', 'PixelFormat'])

	# get node values that will be changed in order to return their values at
	# the end of the example
	pixelformat_initial_value = nodes['PixelFormat'].value

	# Set pixel format to PolarizedAngles_0d_45d_90d_135d_BayerRG8
	pixel_format_name = 'PolarizedAngles_0d_45d_90d_135d_BayerRG8'
	print(f'{TAB1}Setting Pixel Format to {pixel_format_name}')
	nodes['PixelFormat'].value = pixel_format_name

	# Grab and save an image buffer -------------------------------------------
	print(f'{TAB1}Starting stream')
	with device.start_stream(1):
		print(f'{TAB2}Acquire image')
		image_buffer = device.get_buffer()  # Optional args
            
		save(image_buffer)

		print(f'{TAB2}Processing the raw input image to suppress reflections')
        
		src_width = image_buffer.width         
		src_height = image_buffer.height
		src_pixel_format = image_buffer.pixel_format
        

		if src_pixel_format != PixelFormat.PolarizedAngles_0d_45d_90d_135d_BayerRG8:
			print("\tError - Input image pixel format [{}] is a non-polarized format".format(src_pixel_format))
			return
        
		src_bpp = image_buffer.bits_per_pixel
		src_step = src_bpp // 8
		

		# Create a new buffer to store the processed image
		dst_width = src_width
		dst_height = src_height
		dst_pixel_format = PixelFormat.BayerRG8
		dst_step = PixelFormat.get_bits_per_pixel(dst_pixel_format) // 8
        
		dst_size = dst_width * dst_height
		dst_data_size = dst_width * dst_height * dst_step
            
		dst_data = (ctypes.c_ubyte * dst_data_size)()
        
		if (src_bpp == 32 or src_bpp == 64):
			suppress_reflection(image_buffer.data, src_step, dst_data, dst_step, dst_size)
                  
		uint8_ptr = ctypes.POINTER(ctypes.c_ubyte)
		dst_data_ptr = ctypes.cast(dst_data, uint8_ptr)
            
		# Save the reflection-corrected polarized image
		output_buffer = BufferFactory.create(dst_data_ptr, dst_data_size, dst_width, dst_height, dst_pixel_format) 
        
		writer_jpg = Writer.from_buffer(output_buffer)
            
		writer_jpg.save(output_buffer, 'images/py_polarization/reflection_suppression.jpg')
		
		print(f'{TAB2}Save the reflection-corrected polarized image to {writer_jpg.saved_images[-1]}')
            
		BufferFactory.destroy(output_buffer)
      
		device.requeue_buffer(image_buffer)
		
		device.stop_stream()
		print(f'{TAB1}Stream stopped')
	
	# Reset the pixel format to its initial value
	nodes['PixelFormat'].value = pixelformat_initial_value
      
	system.destroy_device()
	print(f'{TAB1}Destroyed all created devices')

if __name__ == '__main__':
	print('\nWARNING:\nTHIS EXAMPLE MIGHT CHANGE THE DEVICE(S) SETTINGS!')
	print('\nExample started\n')
	example_entry_point()
	print('\nExample finished successfully')
