import functions as fu
import mic
import os
import time
import tkinter as tk
import tkinter.scrolledtext as tkst
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter.filedialog import askopenfilename, askopenfilenames, askdirectory
from tempfile import TemporaryDirectory

class MainApplication:
    def __init__(self, master):
        self.default_index_filename = 'index.pkl'
        self.tmpdir = TemporaryDirectory()

        # Instantiate window
        self.master = master
        self.master.configure(bg='white')
        self.screenw = self.master.winfo_screenwidth()
        self.screenh = self.master.winfo_screenheight()
        self.master.geometry(f'500x400+{int(self.screenw/3)}+{int(self.screenh/3)}')

        ###############################################################
        # Menu
        menu = tk.Menu(self.master)
        master.config(menu=menu)

        menu_index = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label='Index', menu=menu_index)
        menu_index.add_command(label='Load index file', command=self.open_index_clicked)
        
        menu_create = tk.Menu(menu_index, tearoff=0)
        menu_create.add_command(label='From files only in the directory (non-recursive)',
                                command=self.create_nonrec_clicked)
        menu_create.add_command(label='From files in directory and its subdirectories (recursive)',
                                command=self.create_rec_clicked)
        menu_index.add_cascade(label='Create from music directory', menu=menu_create)

        menu_update = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label='Update index', menu=menu_update, state='disabled')
        menu_update.add_command(label='From music directory', command=self.update_index_from_dir_clicked)
        menu_update.add_command(label='From files', command=self.update_index_from_files_clicked)
        self.menu = menu

        ###############################################################
        # Set up container grid
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_rowconfigure(1, weight=1, minsize=150)
        self.master.grid_rowconfigure(2, weight=1)

        # Create containers
        self.frame_find = tk.Frame(self.master)
        self.frame_results = tk.Frame(self.master)
        self.frame_status = tk.Frame(self.master)

        # Place containers
        self.frame_find.grid(row=0, padx=3, pady=3, sticky='we')
        self.frame_results.grid(row=1, padx=3, pady=3, sticky='nswe')
        self.frame_status.grid(row=2, padx=3, pady=3, sticky='nswe')

        # Control resizing of frames by their child widgets
        self.frame_results.pack_propagate(False)
        self.frame_status.pack_propagate(False)
        ###############################################################
        # Find frame
        self.label_find = tk.Label(self.frame_find, text='To identify music, open a sample or record a 5 second sample',
                                    bd='3', fg='blue', font='Helvetica 9 bold')

        self.button_record = tk.Button(self.frame_find, text='Record Sample',
                                      command=self.record_clicked)
        self.button_open_sample = tk.Button(self.frame_find, text='Open Music Sample',
                                      command=self.open_sample_clicked)

        self.label_find.grid(row=0, columnspan=2, sticky='w')
        self.button_open_sample.grid(row=1, column=0, sticky='nswe')
        self.button_record.grid(row=1, column=1, sticky='nswe')

        self.button_open_sample['state'] = 'disabled'
        self.button_record['state'] = 'disabled'

        self.frame_find.grid_rowconfigure(0, weight=0)
        self.frame_find.grid_rowconfigure(1, weight=1)
        self.frame_find.grid_columnconfigure(0, weight=1)
        self.frame_find.grid_columnconfigure(1, weight=1)

        ###############################################################
        # Results frame
        self.label_results = tk.Label(self.frame_results, text='Result',
                                      bd='1', fg='blue', font='Helvetica 9 bold')
        self.space_results = tkst.Text(master=self.frame_results,
                                                wrap='word',
                                                bg='white',
                                                font='Arial 9',
                                                height=2)
        self.label_other_results = tk.Label(self.frame_results,
            text='If sample doesn\'t match the found track, take a look at other ones:')
        self.space_other_results = tkst.Text(master=self.frame_results,
                                                wrap='word',
                                                bg='white',
                                                font='Arial 8')
        self.space_results.configure(state='disabled')
        self.space_other_results.configure(state='disabled')

        self.label_results.pack(anchor='w')
        self.space_results.pack(fill=tk.BOTH)
        self.label_other_results.pack(anchor='w')
        self.space_other_results.pack(fill=tk.BOTH)
        
        ###############################################################
        # Status frame
        self.label_status = tk.Label(self.frame_status, text='Status', bd='3',
                                     fg='blue', font='Helvetica 9 bold')
        self.space_status = tkst.ScrolledText(master=self.frame_status,
                                                wrap='word',
                                                bg=self.frame_status.cget('bg'),
                                                font='Courier 7')
        self.space_status.configure(state='disabled')

        self.label_status.pack(anchor='w')
        self.space_status.pack(fill=tk.BOTH)
        
        ###############################################################
        self.master.update()
        self.master.minsize(self.master.winfo_width(), self.master.winfo_height())
        
    def __del__(self):
        self.tmpdir.cleanup()

    ###############################################################
    def create_index_from_dir(self, recursive):
        try:
            dir_path = tk.filedialog.askdirectory(initialdir=os.getcwd())
            if dir_path:
                self.write_to_text_widget(self.space_status, f'Indexing audio files in {dir_path}...')

                self.index = fu.create_index(dir_path, recursive)
                if self.index:
                    self.index_filename = self.default_index_filename
                    self.write_to_text_widget(self.space_status, f'Saving index to file {self.index_filename}...')
                    fu.save_index_file(self.index, self.index_filename)
                    self.write_to_text_widget(self.space_status, f'Index has been built, saved, and loaded. You can start searching.')
                    self.enable_widgets()
                else:
                    self.write_to_text_widget(self.space_status, f'Indexing audio files in {dir_path} failed. No files in provided directory?')
        except Exception as e:
            self.write_to_text_widget(self.space_status, f'Something went wrong: {e}')

    def create_rec_clicked(self):
        self.create_index_from_dir(recursive=True)

    def create_nonrec_clicked(self):
        self.create_index_from_dir(recursive=False)

    def load_index_on_start(self):
        self.index_filename = self.default_index_filename
        self.write_to_text_widget(self.space_status, f'Reading index file "{self.index_filename}"...')
        self.index = None
        self.index = fu.open_index_file(self.index_filename)
        if self.index:
            self.write_to_text_widget(self.space_status, 'Index has been loaded. You can start searching.')
            self.enable_widgets()
        else:
            self.write_to_text_widget(self.space_status, 'No index found. Please create or load it to use the app.')

    def open_index_clicked(self):
        try:
            self.index_filename = tk.filedialog.askopenfilename(initialdir=os.getcwd())
            if self.index_filename:
                self.write_to_text_widget(self.space_status, f'Reading index file "{self.index_filename}"...')
                self.index = fu.open_index_file(self.index_filename)
                if self.index:
                    self.write_to_text_widget(self.space_status, 'Index has been loaded. You can start searching.')
                    self.enable_widgets()
            else:
                pass
        except Exception as e:
            self.write_to_text_widget(self.space_status, f'Something went wrong: {e}')

    def update_index_from_dir_clicked(self):
        try:
            dir_path = tk.filedialog.askdirectory(initialdir=os.getcwd())
            if dir_path:
                self.write_to_text_widget(self.space_status, f'Updating index with audio files in {dir_path}...')
                fu.update_index(self.index, dir_path)
                fu.save_index_file(self.index, self.index_filename)
                self.write_to_text_widget(self.space_status, f'Index has been updated and saved.')
        except Exception as e:
            self.write_to_text_widget(self.space_status, f'Updating index with audio files in {dir_path} failed: {e}')

    def update_index_from_files_clicked(self):
        try:
            files = tk.filedialog.askopenfilenames(initialdir=os.getcwd())
            if files:
                self.write_to_text_widget(self.space_status, f'Updating index with selected audio files...')
                fu.update_index(self.index, files)
                fu.save_index_file(self.index, self.index_filename)
                self.write_to_text_widget(self.space_status, f'Index has been updated and saved.')
        except Exception as e:
            self.write_to_text_widget(self.space_status, f'Updating index with selected audio files failed: {e}')

    def open_sample_clicked(self):
        if self.index:
            try:
                sample_filename = tk.filedialog.askopenfilename(initialdir=os.getcwd())
                if sample_filename:
                    self.find_best_matches(sample_filename)
            except Exception as e:
                self.write_to_text_widget(self.space_status, f'Something went wrong: {e}')
        else:
            self.write_to_text_widget(self.space_status, 'Please create or load index.')

    def record_clicked(self):
        popup = tk.Tk()
        popup.wm_title('Recording sample')
        popup.geometry(f'+{int(self.screenw/2.5)}+{int(self.screenh/2.5)}')
        button_cancel = tk.Button(popup, text='Cancel', command=popup.destroy)
        
        fig, ax = plt.subplots()

        figure_canvas = FigureCanvasTkAgg(fig, master=popup)
        figure_canvas.get_tk_widget().pack()
        button_cancel.pack()

        self.write_to_text_widget(self.space_status, 'Recording sample...')
        sample_filename = mic.record_draw_save(fig, ax, save_dir=self.tmpdir.name)
        if sample_filename:
            self.write_to_text_widget(self.space_status, 'Sample recorded.')
            popup.destroy()
            self.find_best_matches(sample_filename)
        else:
            self.write_to_text_widget(self.space_status, 'Sample recording cancelled.')
    
    def find_best_matches(self, sample_filename):
        self.delete_text_from_widget(self.space_results)
        self.delete_text_from_widget(self.space_other_results)
        self.write_to_text_widget(self.space_status, 'Processing sample...')
        sample = fu.create_index(sample_filename)
        self.write_to_text_widget(self.space_status, 'Finding best matches...')
        offset_diffs = fu.get_offset_diffs(sample, self.index)
        best_matches = fu.get_best_matches(offset_diffs)
        self.write_to_text_widget(self.space_results, f'#1. {best_matches[0]}', where='1.0')
        for i, match in enumerate(best_matches[1:6]):
            self.write_to_text_widget(self.space_other_results, f'#{i+2}. {match}')
        self.write_to_text_widget(self.space_status, f'Best matches for the provided sample found, check results.')
    
    def write_to_text_widget(self, widget, content, where='end'):
        widget.configure(state='normal')
        widget.insert(where, f'{content}\n')
        widget.configure(state='disabled')
        widget.see(where)
        self.master.update_idletasks()

    def delete_text_from_widget(self, widget):
        widget.configure(state='normal')
        widget.delete('1.0', 'end')
        widget.configure(state='disabled')
    
    def enable_widgets(self):
        self.button_open_sample['state'] = 'normal'
        self.button_record['state'] = 'normal'
        self.menu.entryconfig(3, state='normal')


def launchApp():
    window = tk.Tk()
    window.title("Razam v0.1")
    c = MainApplication(window)
    window.after(500, c.load_index_on_start)
    window.mainloop()
    
if __name__=='__main__':
    launchApp()