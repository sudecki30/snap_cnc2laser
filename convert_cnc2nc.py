import re
import tkinter as tk
from tkinter import *
from tkinter import ttk
from tkinter import filedialog as fd
from tkinter.messagebox import showinfo
import os

class Limiter(ttk.Scale):
    """ ttk.Scale sublass that limits the precision of values. """

    def __init__(self, *args, **kwargs):
        self.precision = kwargs.pop('precision')  # Remove non-std kwarg.
        self.chain = kwargs.pop('command', lambda *a: None)  # Save if present.
        super(Limiter, self).__init__(*args, command=self._value_changed, **kwargs)

    def _value_changed(self, newvalue):
        newvalue = int(float(newvalue))
        self.winfo_toplevel().globalsetvar(self.cget('variable'), (newvalue))
        self.chain(newvalue)

class GUI:
    def __init__(self,root):
        self.laser_power = tk.IntVar(root)
        self.laser_power.set(0)
        self.file=""

        open_button = ttk.Button(root, text='Open a File', command= lambda:self.select_file())
        convert_button = ttk.Button(root, text='Convert', command= lambda:self.convert())
        spin = tk.Spinbox(root, textvariable=self.laser_power, wrap=True, width=10)
        slide = Limiter(root, variable=self.laser_power, orient='horizontal', length=200, precision=1)

        spin['to'] = 100.0
        spin['from'] = 0.0
        spin['increment'] = 1
        slide['to'] = 100.0
        slide['from'] = 0.0

        laser_label = ttk.Label(root, text="Laser power:")
        laser_label.grid(row=0, column=0, columnspan=2)

        spin.grid(row=1, column=1)
        slide.grid(row=1, column=0)

        empty_label = ttk.Label(root, text="")
        empty_label.grid(row=2, column=0, columnspan=2)

        open_button.grid(row=3, columnspan=2)

        convert_button.grid(row=3, column=1)

    def select_file(self):
        filetypes = (('CNC files', '*.cnc'), ('All files', '*.*'))
        self.file = fd.askopenfilename(title='Open a file', initialdir='/', filetypes=filetypes)

    def convert(self):
        convert_file(self.file,self.laser_power.get())

def change_Gvalue(line:str,g_value):
    line_list = list(line)
    line_list[1] = "{}".format(g_value)
    return ''.join(line_list)

def get_value(line):
    x=0
    y=0
    z=0
    speed=0
    m = re.search(r'X(-?\d+\.\d+) Y(-?\d+\.\d+)', line)
    if m:
        x=float(m.group(1))
        y=float(m.group(2))

    m = re.search(r'Z(-?\d+\.\d+)+', line)
    if m:
        z = float(m.group(1))

    m = re.search(r'F(\d+)+', line)
    if m:
        speed=float(m.group(1))
    return x,y,z,speed




def convert_file(file,laser_power):
    # file=r"C:\Users\guira\Documents\impression 3D\Cannes + Laser\Laser pass.cnc"
    if not os.path.isfile(file):
        showinfo(title="File doesn't exist", message=file)
        return

    # create for start project
    cmd_start = "M2000 W1 P100\nM2000 W2 P100\nM3 S0\nM9\nM2000 L23 P1\n"

    # read file and correct it to corespond to laser file
    with open(file, 'r') as load_profile:
        all_lines = load_profile.readlines()
        all_lines_corected = []
        # init
        i = 0
        start_laser = 0
        start = 0
        print(laser_power)
        laser_power=int(laser_power)
        while i < len(all_lines):
            # studies only lines with coordinates
            if "X" in all_lines[i]:
                x_1, y_1, z_1, speed_1 = get_value(all_lines[i])
                x, y, z, speed = get_value(all_lines[i - 1])

                # case to stop laser (detect Z hop or increase speed) only when laser is on
                if (z_1 == 5 or z_1 == 15 or (speed_1 > speed and speed > 0 and speed_1 > 0)) and start_laser == 1:
                    all_lines[i] = change_Gvalue(all_lines[i], 0)
                    all_lines_corected.append(all_lines[i])
                    all_lines[i + 1] = change_Gvalue(all_lines[i + 1], 0)
                    all_lines_corected.append(all_lines[i + 1])
                    i += 2
                    start_laser = 0

                # modify G1 to G0 if laser is off (and opposite)
                if start_laser == 1:
                    all_lines[i] = change_Gvalue(all_lines[i], 1)
                else:
                    all_lines[i] = change_Gvalue(all_lines[i], 0)

                # detect if coordinate change with corect speed and not z hop
                if x != 0 and x_1 != 0 and (x != x_1 or y != y_1) and speed_1 != 3000 and z != 5:
                    # no fist time, we need only to add S with laser power 255 scale
                    if start_laser == 0 and start == 1:
                        all_lines[i] = all_lines[i][:-1] + " S{}\n".format(int(255 / 100 * laser_power))
                        all_lines[i] = change_Gvalue(all_lines[i], 1)
                        start_laser = 1
                    # first time init laser and start iti
                    if start == 0:
                        start = 1
                        all_lines_corected.append(cmd_start)
                        all_lines[i] = all_lines[i][:-1] + " S{}\n".format(int(255 / 100 * laser_power))
                        all_lines[i] = change_Gvalue(all_lines[i], 1)
                        start_laser = 1

            # search the end to stop laser definitely
            if "M5" in all_lines[i]:
                all_lines[i] = all_lines[i][:-1] + ' S0\n'

            # delete start code cnc
            if not "M3 P100" in all_lines[i] and not "G4 S2" in all_lines[i]:
                all_lines_corected.append(all_lines[i])
            i += 1
    # add end Gcode
    all_lines_corected.append("G91\nG0 Z0 F150\nG90\n")

    # save
    with open(file[:-3] + "nc", 'w') as fp:
        for item in all_lines_corected:
            fp.write(f"{item}")
    showinfo(title="Convertion done", message="New file: {}".format(file[:-3] + "nc"))

if __name__ == "__main__":

    root = tk.Tk()
    root.title('Tkinter Open File Dialog')
    root.resizable(False, False)
    root.geometry('300x100')
    gui=GUI(root)
    root.mainloop()





