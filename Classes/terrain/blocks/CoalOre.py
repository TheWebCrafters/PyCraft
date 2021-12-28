import Classes as pycraft

class Block(pycraft.Block):
    def __init__(self, *args, **kwargs):
        """
        CoalOre
        
        * Initializes the block
        
        :parent: the parent window
        """
        super().__init__("CoalOre", *args, **kwargs)

        self.texture = {
            "top": self.parent.textures["stone"],
            "front": self.parent.textures["coal_ore"],
            "back": self.parent.textures["stone"],
            "left": self.parent.textures["stone"],
            "right": self.parent.textures["stone"],
            "bottom": self.parent.textures["stone"]
        }