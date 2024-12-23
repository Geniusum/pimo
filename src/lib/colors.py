class Colors():
    def __init__(self, activated:bool=True):
        self.activated = activated
        self.fore = {
            "black": 30,
            "red": 31,
            "green": 32,
            "yellow": 33,
            "blue": 34,
            "purple": 35,
            "cyan": 36,
            "white": 37
        }
        self.styles = {
            "none": 0,
            "bold": 1,
            "underline": 2,
            "neg1": 3,
            "neg2": 4
        }
        self.back = {
            "black": 40,
            "red": 41,
            "green": 42,
            "yellow": 43,
            "blue": 44,
            "purple": 45,
            "cyan": 46,
            "white": 47,
            "none": 49
        }
    
    def get(self, fore:str="white", style:str="none", back:str="none"):
        if self.activated: return f"\33[;{self.styles[style]};{self.fore[fore]};{self.back[back]}m"
        return ""