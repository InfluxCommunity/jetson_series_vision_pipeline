## Pipeline Code

*Note: A fair chunk of the code comes from NVIDIA DeepStream examples which can be found [here](https://github.com/NVIDIA-AI-IOT/deepstream_python_apps/tree/v1.0.3). My demo has been based on version 5.1, please note that when 6.0 releases it may contain breaking changes.*

  

My aim was to improve the readability and overall modularity of the code as we will be extending to include our own data model for Telegraf and InfluxDB. Here is a map of project files (Please forgive the butchering of a class diagram) :

  
![](cd)

  

Figure 6 - Solution Class Diagram

Let’s dive into some of the python code.

### Element Factory

``` PYTHON

<element_var> = Gst.ElementFactory.make(“<GStreamer_Element>”, “<unique_name>”)

# Example

self.source = Gst.ElementFactory.make("v4l2src", "usb-cam-source")

```

This method generates new Gstreamer elements from within our python code. We use it to generate each component of our pipeline from the DeepStreamer ecosystem.

  

### Set Property

```PYTHON

<element_var>.set_property(“<property_name>”, “<value>”)

# Example

self.source.set_property('device', cam)

```

This method allows us to define properties for our GStreamer elements. The pro’s of defining element properties this way is that they can be set dynamically during runtime. If all your properties are considered static then you can also use a text file:

  

```PYTHON

self.pgie.set_property('config-file-path', "model_config.txt")

```

This provides more readability from elements with lengthy property lists.

  

### Add and Link

```PYTHON

<pipeline_var>.add(<element_var>)

<element_var_1>.link(<element_var_2>)

# Example

pipeline.add(self.source)

pipeline.add(self.caps_v4l2src)

self.source.link(self.caps_v4l2src)

```

Add() and link() are two key functions to the construction of our pipeline. Add assigns a Gstreamer element to a “bin” (which we are referring to as pipeline). An element can only be owned by one bin. Link adds the source element to the destination element. In other words the next link in the pipeline.
