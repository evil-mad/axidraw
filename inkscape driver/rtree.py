class Index:

    bboxes = []

    def __init__(self, bboxes):
        self.bboxes = bboxes
    
    def intersection(self, bbox):
        return [
            index
            for (index, _) in self.bboxes
        ]
