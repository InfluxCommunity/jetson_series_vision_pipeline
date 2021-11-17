## Vision AI Pipeline

Now that you have enough background knowledge to be dangerous let’s take a look at our vision pipeline. I am going to break it down into two diagrams:

  

![basic_gstreamer_pipeline](/docs/images/Vision_Pipeline_Overview.png)

Figure 3 ~ Vision AI Pipeline (High level)

  

For this solution, we will be using a USB webcam attached to our NVIDIA Jetson. Our Vision AI Pipeline will ingest the raw frames produced by the USB webcam and feed them through an object detection model. The model is trained to detect four categories; people, cars, bikes and road signs (road sign detection has been disabled from this use case as they do not provide any benefit for this demo). The produced inference results are then used within two parallel output plugins:

1.  RTSP (Real-Time Streaming Protocol) Server: This allows us to send our video frames to a network-accessible endpoint. Meaning we can remotely monitor the output from the webcam. The RTSP Protocol has commonly been used within CCTV (Closed-circuit television) architectures.
    
2.  MQTT Client: In short the MQTT client allows us to send our detection results (Otherwise known as inference results) to Telegraf and intern InfluxDB for further analytics. We will discuss this in further detail later.
    

  

So what does our vision AI pipeline look like in Gstreamer components:

  

![gstreamer_vision_pipeline](/docs/images/gstreamer_vision_pipeline.png)

Figure 4 ~ Vision AI Pipeline (GStreamer)

Feels like a lot right? Let’s break down the components and explain the role of each component:

1.  V4l2src - Used to capture video from Video4Linux devices (In our case the webcam).
    
2.  Capsfilter - Used to enforce limitations on the data stream. In our use case, we enforce a maximum rate of 30 frames per second and an x-raw video format. This provides security for downstream nodes which expect an x-raw video format and limits frame throughput.
    
3.  Videoconvert - Used to convert video frames between a variety of video formats. We use this to ensure a superset of raw formats is supported (videoconvert will automatically select a format understood by the next node).
    
4.  Nvvideoconvert - This might seem a little confusing why we perform two conversions in conjunction, we are getting pretty low level at this point. Essentially we use this plugin to pass our frame set into a DMA (Direct Memory Access) buffer (accessible both by the CPU and GPU).
    
5.  Capsfilter - Again we enforce the frame format. We converted our raw frames to NVMM (NVIDIA memory module) during Nvvideoconvert.
    
6.  Nvstreammux - Otherwise known as a muxer it allows us to batch frames from multiple input sources and scale them. Our use case has only one input source so we essentially store 1 frame and convert it to a resolution of 1920 by 1080 if required. It is an expectation of our inference engine which we will discuss next.
    
7.  Nvinfer - The main event! Our frame is now passed to the primary inference engine. I am going to explain this feature in more detail later. For now, let's cover the basics. Nvinfer has the ability to optimize different neural network frameworks using TensorRT. In this pipeline, we provide a mode_config.txt file containing the properties for the inference engine (Again we will discuss this later).
    
8.  Nvvideoconvert - We use another converter to automatically convert our frames from NV12 format to RGBA (This is a requirement of nvdsosd).
    
9.  Nvdsosd - This plugin allows us to draw bounding boxes, text and ROI polygons. These are drawn based on the provided metadata from the inference engine. In our case, these will be coordinates for the bounding boxes.
    
10.  Nvvideoconvert & capsfilter - We now begin to prepare our modified frames for network transport. To do this we use a final converter and caps filter to change our frame format to I420.
    
11.  Nvv4l2h264enc - This plugin encodes our frames into the H264 codec. H264 is a topic in itself but in short, this allows us to transmit video frames with vastly fewer bandwidth requirements than raw frames.
    
12.  Rtph264pay - Encodes our H264 video frames into RTP (Real-time Transport Protocal) packets.
    
13.  udpsink - This allows us to stream our RTP packets to the RTSP server.
    

  

Hopefully, this gives you an idea of the flexibility we have at our disposal. In summary, we requested raw video frames from our webcam, converted them into a memory format that is accessible by the GPU and passed them through an AI engine before delivering them to our RTSP server.

  

Before we move onto our InfluxDB integration let’s break down the MVPs of our Pipeline (NVinfer and the model).

### The Inference Engine and Model

Before we deep dive let’s discuss what an Inference engine and model is:

-   Inference Engine - provides the necessary functions and optimizations for running a neural network on our chosen device. An inference engine’s API provides simplified methods for interfacing with your model such as inputting frames for processing and producing the output tensor.
    
-   Model - Our model is essentially a pre-trained neural network. In traditional programming, we provide the rules for our algorithms to act upon to generate an answer (if it has four legs and barks then equals dog). Neural networks are provided with the input data and the answers and deduce their own rules for achieving the answer.
    

As previously mentioned the NVinfer plugin hosts and runs our model. NVinfer features include:

-   Optimization - NVinfer will automatically optimize model frameworks (Caffe, UFF and ONNX) using the TensorRT library.
    
-   Transformation - NVinfer ensures that frames are scaled and transformed appropriately based on the input requirements of the model.
    
-   Processing - NVinfer runs the TensorRT inference engine which runs our optimized model. This produces a meta containing the prediction results of the model. The TensorRT engine supports (Multi-class object detection, multi-label classification and Segmentation).
    

If you want more information on the TensorRT engine I highly recommend you check out this [blog on Medium](https://medium.com/@abhaychaturvedi_72055/understanding-nvidias-tensorrt-for-deep-learning-model-optimization-dad3eb6b26d9).

  

So what does our Nvinfer configuration look like:

```Text

[property]

gpu-id=0

net-scale-factor=0.0039215697906911373

model-file=../model/Primary_Detector/resnet10.caffemodel

proto-file=../model/Primary_Detector/resnet10.prototxt

model-engine-file=../model/Primary_Detector/resnet10.caffemodel_b1_gpu0_int8.engine

labelfile-path=../model/Primary_Detector/labels.txt

int8-calib-file=../model/Primary_Detector/cal_trt.bin

force-implicit-batch-dim=1

batch-size=1

network-mode=1

num-detected-classes=4

interval=0

process-mode=1

model-color-format=0

gie-unique-id=1

output-blob-names=conv2d_bbox;conv2d_cov/Sigmoid

cluster-mode=2

network-type=0

  

[class-attrs-all]

pre-cluster-threshold=0.2

eps=0.2

group-threshold=1

```

In short, we are providing a [Caffe mode](https://catalog.ngc.nvidia.com/orgs/nvidia/teams/iva/models/tlt_resnet10_ssd)l based on the [Resnet neural network architecture](https://towardsdatascience.com/an-overview-of-resnet-and-its-variants-5281e2f56035). The proto-file provides a description of the Caffemodel layers. Label’s file provides human-readable labels for our tensor results.

  

Lastly, let’s talk about the model. Our model has been created and trained using the Caffe deep learning framework. Caffe in short allows to you create or modify neural network architectures by configuring its layer parameters. For more information on Caffe check out their [website](https://caffe.berkeleyvision.org/). Our neural network architecture is ResNet (residual neural network). This architecture was designed by Microsoft to solve a [performance degradation problem](https://www.youtube.com/watch?v=RQ4sMZiciuI&t=168s) in Deep neural networks. Our model has been trained on 4 key items (people, bikes, cars and signs). We have the advantage that our model is publicly acceptable and trained on thousands of images.

![sample_data](/docs/images/sample_data.png)

Figure 5 - Visual representation of a training set
