import pyds
from gi.repository import  Gst
from mqtt_client import mqtt_client
from data_structures.inference import inference

PGIE_CLASS_ID_VEHICLE = 0
PGIE_CLASS_ID_BICYCLE = 1
PGIE_CLASS_ID_PERSON = 2
PGIE_CLASS_ID_ROADSIGN = 3



BROKER_CONNECT = True
INFERENCE = inference()



def osd_sink_pad_buffer_probe(pad,info,u_data):
    global BROKER_CONNECT
    global INFERENCE

    frame_number=0
    num_rects=0
    obj_counter = {
        PGIE_CLASS_ID_VEHICLE:0,
        PGIE_CLASS_ID_PERSON:0,
        PGIE_CLASS_ID_BICYCLE:0,
        PGIE_CLASS_ID_ROADSIGN:0
    }

    try:
        mqttClient = mqtt_client("localhost", 1883 , "Inference_results")
        mqttClient.connect_client()
    except:
        print("could not connect to MQTT Broker")
        BROKER_CONNECT = False

    gst_buffer = info.get_buffer()
    if not gst_buffer:
        print("Unable to get GstBuffer ")
        return

    # Retrieve batch metadata from the gst_buffer
    # Note that pyds.gst_buffer_get_nvds_batch_meta() expects the
    # C address of gst_buffer as input, which is obtained with hash(gst_buffer)
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list
    while l_frame is not None:
        try:
            # Note that l_frame.data needs a cast to pyds.NvDsFrameMeta
            # The casting is done by pyds.NvDsFrameMeta.cast()
            # The casting also keeps ownership of the underlying memory
            # in the C code, so the Python garbage collector will leave
            # it alone.
           frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break

        frame_number=frame_meta.frame_num
        num_rects = frame_meta.num_obj_meta
        l_obj=frame_meta.obj_meta_list

        unique_obj_id = 0

        while l_obj is not None:
            try:
                # Casting l_obj.data to pyds.NvDsObjectMeta
                obj_meta=pyds.NvDsObjectMeta.cast(l_obj.data)
            except StopIteration:
                break
            
            
            obj_counter[obj_meta.class_id] += 1
            unique_obj_id +=1

            INFERENCE.add_detection({"classID": obj_meta.class_id,
                                     "label": obj_meta.obj_label,  
                                     "confidence": obj_meta.confidence,
                                     "coor_left": obj_meta.rect_params.left,
                                     "coor_top": obj_meta.rect_params.top,
                                     "box_width": obj_meta.rect_params.width,
                                     "box_height": obj_meta.rect_params.height,
                                     "objectID": obj_meta.object_id,
                                     "unique_com_id": "OBJ"+str(unique_obj_id)
                                                          })
            
            try: 
                l_obj=l_obj.next
            except StopIteration:
                break
        # Do somthing with Inference data -> Overlay 
        #                                 -> MQTT

        overlay(batch_meta, frame_meta, frame_number, num_rects, obj_counter)

        if BROKER_CONNECT == True and not (frame_number%30):
            publish_to_mqtt(mqttClient, frame_number, num_rects)

        try:
            INFERENCE.reset()
            l_frame=l_frame.next
        except StopIteration:
            break
			
    return Gst.PadProbeReturn.OK	




def publish_to_mqtt(mqttClient, frame_number, num_rects) -> None:

    current_num_rects = 0

    #if num_rects != current_num_rects:
    INFERENCE.set_total_obj(num_rects)
    INFERENCE.set_detection_frame(frame_number)
    data = INFERENCE.return_data_sample()
    topic = "inference"


    mqttClient.publish_to_topic(topic, data)
    print(data, flush=True)
    current_num_rects = num_rects






def overlay(batch_meta, frame_meta, frame_number, num_rects, obj_counter) -> None:
           # Acquiring a display meta object. The memory ownership remains in
        # the C code so downstream plugins can still access it. Otherwise
        # the garbage collector will claim it when this probe function exits.
        display_meta=pyds.nvds_acquire_display_meta_from_pool(batch_meta)
        display_meta.num_labels = 1
        py_nvosd_text_params = display_meta.text_params[0]
        # Setting display text to be shown on screen
        # Note that the pyds module allocates a buffer for the string, and the
        # memory will not be claimed by the garbage collector.
        # Reading the display_text field here will return the C address of the
        # allocated string. Use pyds.get_string() to get the string content.
        py_nvosd_text_params.display_text = "Frame Number={} Number of Objects={} Vehicle_count={} Person_count={}".format(frame_number, num_rects, obj_counter[PGIE_CLASS_ID_VEHICLE], obj_counter[PGIE_CLASS_ID_PERSON])

        # Now set the offsets where the string should appear
        py_nvosd_text_params.x_offset = 10
        py_nvosd_text_params.y_offset = 12

        # Font , font-color and font-size
        py_nvosd_text_params.font_params.font_name = "Serif"
        py_nvosd_text_params.font_params.font_size = 10
        # set(red, green, blue, alpha); set to White
        py_nvosd_text_params.font_params.font_color.set(1.0, 1.0, 1.0, 1.0)

        # Text background color
        py_nvosd_text_params.set_bg_clr = 1
        # set(red, green, blue, alpha); set to Black
        py_nvosd_text_params.text_bg_clr.set(0.0, 0.0, 0.0, 1.0)
        # Using pyds.get_string() to get display_text as string
        
        pyds.nvds_add_display_meta_to_frame(frame_meta, display_meta)