from common.is_aarch_64 import is_aarch64
import sys
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import  Gst

class deepstream_pipeline:
    def __init__(self) -> None:
        self.updsink_port_num = 5400
            # videoconvert to make sure a superset of raw formats are supported
        self.vidconvsrc = Gst.ElementFactory.make("videoconvert", "convertor_src1")
        if not self.vidconvsrc:
            sys.stderr.write(" Unable to create videoconvert \n")

        # nvvideoconvert to convert incoming raw buffers to NVMM Mem (NvBufSurface API)
        self.nvvidconvsrc = Gst.ElementFactory.make("nvvideoconvert", "convertor_src2")
        if not self.nvvidconvsrc:
            sys.stderr.write(" Unable to create Nvvideoconvert \n")

        self.caps_vidconvsrc = Gst.ElementFactory.make("capsfilter", "nvmm_caps")
        if not self.caps_vidconvsrc:
            sys.stderr.write(" Unable to create capsfilter \n")

        # Create nvstreammux instance to form batches from one or more sources.
        self.streammux = Gst.ElementFactory.make("nvstreammux", "Stream-muxer")
        if not self.streammux:
            sys.stderr.write(" Unable to create NvStreamMux \n")

        # Use nvinfer to run inferencing on camera's output,
        # behaviour of inferencing is set through config file
        self.pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
        if not self.pgie:
            sys.stderr.write(" Unable to create self.pgie \n")

    # Use convertor to convert from NV12 to RGBA as required by self.nvosd
        self.nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "convertor")
        if not self.nvvidconv:
            sys.stderr.write(" Unable to create self.nvvidconv \n")
        
        # Create OSD to draw on the converted RGBA buffer
        self.nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")
        if not self.nvosd:
            sys.stderr.write(" Unable to create self.nvosd \n")
        self.nvvidconv_postosd = Gst.ElementFactory.make("nvvideoconvert", "convertor_postosd")
        if not self.nvvidconv_postosd:
            sys.stderr.write(" Unable to create self.nvvidconv_postosd \n")
        
        # Create a caps filter
        self.caps = Gst.ElementFactory.make("capsfilter", "filter")
        self.caps.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM), format=I420"))


        print("Creating Source \n ")
        self.source = Gst.ElementFactory.make("v4l2src", "usb-cam-source")
        if not self.source:
            sys.stderr.write(" Unable to create Source \n")

        self.caps_v4l2src = Gst.ElementFactory.make("capsfilter", "v4l2src_caps")
        if not self.caps_v4l2src:
            sys.stderr.write(" Unable to create v4l2src capsfilter \n")


        print("Creating Video Converter \n")

    def create_pipeline(self, pipeline, cam, codec, bitrate):


        # Adding videoconvert -> nvvideoconvert as not all
        # raw formats are supported by nvvideoconvert;
        # Say YUYV is unsupported - which is the common
        # raw format for many logi usb cams
        # In case we have a camera with raw format supported in
        # nvvideoconvert, GStreamer plugins' capability negotiation
        # shall be intelligent enough to reduce compute by
        # videoconvert doing passthrough.

        # Make the encoder
        if codec == "H264":
            encoder = Gst.ElementFactory.make("nvv4l2h264enc", "encoder")
            print("Creating H264 Encoder")
        elif codec == "H265":
            encoder = Gst.ElementFactory.make("nvv4l2h265enc", "encoder")
            print("Creating H265 Encoder")
        if not encoder:
            sys.stderr.write(" Unable to create encoder")
        encoder.set_property('bitrate', bitrate)
        if is_aarch64():
            encoder.set_property('preset-level', 1)
            encoder.set_property('insert-sps-pps', 1)
            encoder.set_property('bufapi-version', 1)
        
        # Make the payload-encode video into RTP packets
        if codec == "H264":
            rtppay = Gst.ElementFactory.make("rtph264pay", "rtppay")
            print("Creating H264 rtppay")
        elif codec == "H265":
            rtppay = Gst.ElementFactory.make("rtph265pay", "rtppay")
            print("Creating H265 rtppay")
        if not rtppay:
            sys.stderr.write(" Unable to create rtppay")
        
        # Make the UDP sink
        
        sink = Gst.ElementFactory.make("udpsink", "udpsink")
        if not sink:
            sys.stderr.write(" Unable to create udpsink")
        
        sink.set_property('host', '224.224.255.255')
        sink.set_property('port', self.updsink_port_num)
        sink.set_property('async', False)
        sink.set_property('sync', 1)
        

        print(f"Playing cam: {cam}")
        self.caps_v4l2src.set_property('caps', Gst.Caps.from_string("video/x-raw, framerate=30/1"))
        self.caps_vidconvsrc.set_property('caps', Gst.Caps.from_string("video/x-raw(memory:NVMM)"))
        self.source.set_property('device', cam)
        self.streammux.set_property('width', 1920)
        self.streammux.set_property('height', 1080)
        self.streammux.set_property('batch-size', 1)
        self.streammux.set_property('batched-push-timeout', 4000000)
        
        self.pgie.set_property('config-file-path', "model_config.txt")
        # Set sync = false to avoid late frame drops at the display-sink
        sink.set_property('sync', False)

        print("Adding elements to Pipeline \n")
        pipeline.add(self.source)
        pipeline.add(self.caps_v4l2src)
        pipeline.add(self.vidconvsrc)
        pipeline.add(self.nvvidconvsrc)
        pipeline.add(self.caps_vidconvsrc)
        pipeline.add(self.streammux)
        pipeline.add(self.pgie)
        pipeline.add(self.nvvidconv)
        pipeline.add(self.nvosd)
        pipeline.add(self.nvvidconv_postosd)
        pipeline.add(self.caps)
        pipeline.add(encoder)
        pipeline.add(rtppay)
        pipeline.add(sink)
        


        # we link the elements together
        # v4l2src -> nvvideoconvert -> mux -> 
        # nvinfer -> nvvideoconvert -> self.nvosd -> video-renderer
        print("Linking elements in the Pipeline \n")
        self.source.link(self.caps_v4l2src)
        self.caps_v4l2src.link(self.vidconvsrc)
        self.vidconvsrc.link(self.nvvidconvsrc)
        self.nvvidconvsrc.link(self.caps_vidconvsrc)

        sinkpad = self.streammux.get_request_pad("sink_0")
        if not sinkpad:
            sys.stderr.write(" Unable to get the sink pad of self.streammux \n")
        srcpad = self.caps_vidconvsrc.get_static_pad("src")
        if not srcpad:
            sys.stderr.write(" Unable to get source pad of self.caps_vidconvsrc \n")
        srcpad.link(sinkpad)
        self.streammux.link(self.pgie)
        self.pgie.link(self.nvvidconv)
        self.nvvidconv.link(self.nvosd)
        self.nvosd.link(self.nvvidconv_postosd)
        self.nvvidconv_postosd.link(self.caps)
        self.caps.link(encoder)
        encoder.link(rtppay)
        rtppay.link(sink)

        return pipeline