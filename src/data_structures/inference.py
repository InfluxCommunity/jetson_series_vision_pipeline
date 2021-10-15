class inference:
    def __init__(self) -> None:
        self.frame = 0
        self.total_obj = 0
        self.inference_results = []

        
         

    def set_detection_frame(self, frame):
            self.frame = frame

    
    def set_total_obj(self, total_obj):
           self.total_obj = total_obj


    def add_detection (self, detection:dict):
        self.inference_results.append(detection)

    
    def reset(self):
        self.frame = 0
        self.total_obj = 0
        self.inference_results = []




    def return_data_sample(self) -> dict:
            return {"detection_frame_number": self.frame, 
                    "total_num_obj": self.total_obj,
                    "inference_results": self.inference_results}
