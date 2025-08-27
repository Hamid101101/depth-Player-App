from ttkbootstrap import Window
from manager_ui import UIManager

def main():
    root = Window(themename="darkly")  # Modern look using ttkbootstrap
    root.title("Depth Player")
    root.geometry("1280x1024")

    app = UIManager(root)
    root.mainloop()

if __name__ == "__main__":
    main()