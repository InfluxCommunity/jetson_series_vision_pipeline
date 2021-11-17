### GStreamer

Quick pivot: GStreamer in short is a framework that allows you to build multimedia based pipelines from an assortment of media processing systems called plugins. An example pipeline looks like this:

  

```bash

gst-launch-1.0 v4l2src ! jpegdec ! xvimagesink

```
![basic_gstreamer_pipeline](/docs/images/basic_gstreamer_pipeline.png)

Figure 2 ~ GStreamer Example

  

As well as GPU acceleration NVIDIA has provided an ecosystem of Vision analytics (Tensor RT) and IoT plugins (MQTT, Kafka) that abstract you from learning base libraries and systems but this is not to say DeepStream is a walk in the park. Hopefully, this guide will show how InfluxDB and Telegraf can be used to accelerate your development of complex solutions such as this.
