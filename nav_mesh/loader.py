import pickle

class RenameUnpickler(pickle.Unpickler):

    def __init__( self, filename, old_module_name, new_module_name ):
        print("Unpickling renameing:", old_module_name, "->", new_module_name)

        self.old_module_name = old_module_name
        self.new_module_name = new_module_name

        pickle.Unpickler.__init__( self, filename )

    def find_class(self, module, name):

        print("find_class:", module, name)

        if self.old_module_name in module:
            print("Found old module name in:", module )
            module = module.replace( self.old_module_name, self.new_module_name )
            print("Replaced by:", module )

        return pickle.Unpickler.find_class( self, module, name )

def renamed_load(file_obj, old_module_name, new_module_name ):
    return RenameUnpickler(file_obj,
            old_module_name,
            new_module_name).load()
