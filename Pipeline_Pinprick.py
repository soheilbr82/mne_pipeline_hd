# -*- coding: utf-8 -*-
"""
Pipeline for group analysis of MEG data
@author: Lau Møller Andersen
@email: lau.moller.andersen@ki.se | lau.andersen@cnru.dk
@github: https://github.com/ualsbombe/omission_frontiers.git

Adapted to Sektion Biomagnetismus Kopfklinik
@author: Martin Schulz
@email: martin.schulz@stud.uni-heidelberg.de
@github: 

Functions to implement:
- plot compare evokeds
- Sensitivity Analysys
- bad epochs handling?
- Baseline SSP?
- Group analasys with condition-list(picking file and trial_type)
- except watershed_bem refurbish the bash commands
- Condition tags for subject/Grand Average Customizing
    - Comparative Plots
- Epoch rejection, when EOG/ECG exceeds certain value
- Source Estimate with MRI-Slides?
- Parameters in File und auf Cond/File angepasst (save params?)
- name --> subject
- beamformer
- evoked dict noch notwendig?
- Subjects as Classes?
- Rating Analysis
- Group analysis for a/b
- plot_evoked_white: Noise update bad_channels in erm according to raw
- implement Phase-Amplitude-Coupling with pactools
"""

#==============================================================================
# IMPORTS
#%%============================================================================
import sys
from os.path import join, isfile
from datetime import datetime
import re
import numpy as np
import mne

from pipeline_functions import io_functions as io
from pipeline_functions import operations_functions as op
from pipeline_functions import plot_functions as plot
from pipeline_functions import subject_organisation as suborg
from pipeline_functions import utilities as ut
#==============================================================================
# WHICH SUBJECT?
#%%============================================================================

# Which File do you want to run?
# Type in the Number of the File in your sub_list.py = Line
    #possible input(examples):
        #'5'
        #'1,7,28'
        #'1-5'
        #'1-4,7,20-26'
        #'all'

which_file = '14-121' # Has to be strings!

which_mri_subject = 'all' # Has to be a string!

which_erm_file = 'all'

which_motor_erm_file = 'all'

#==============================================================================
# INITIALIZATION GUIS
#%%============================================================================
exec_ops = ut.choose_function()
#==============================================================================
# PARAMETERS
#%%============================================================================
#parameters_start
#OS
n_jobs = -1 #number of processor-cores to use, -1 for auto
enable_cuda = False # Using CUDA on supported graphics card e.g. for filtering
                    # cupy and appropriate CUDA-Drivers have to be installed
                    # https://mne-tools.github.io/dev/advanced_setup.html#advanced-setup
                    
# should files be overwritten
overwrite = True # this counts for all operations below that save output
save_plots = True # should plots be saved

# raw
predefined_bads = [6,7,8,26,59,60,97]
lowpass = 80 # Hz
highpass = 1 # Hz # at least 1 if to apply ICA

# events
adjust_timeline_by_msec = -95 #delay to stimulus in ms

# epochs
min_duration = 0.005 # s
time_unit = 's'
tmin = -0.500 # s
tmax = 2.000 # s
baseline = (-0.500, -0.100) # [s]
autoreject = 1 # set 1 for autoreject
overwrite_ar = 0 # if to calculate new thresholds or to use previously calculated
reject = dict(grad=8000e-13) # if not reject with autoreject
flat = dict(grad=1e-15)
reject_eog_epochs=False
decim = 1 # downsampling factor
event_id = {'LBT':1,'mot_start':2,'offset':4,'start':32}

# evokeds
detrend = False # somehow not working on all data

#TFA
TF_Morlet_Freqs = np.logspace(*np.log10([6, 35]), num=8)

#ICA
eog_channel = 'EEG 001'
ecg_channel = 'EEG 003'

# Layout (our special Neuromag-122-Layout, should be in same directory as script)
layout = mne.channels.read_layout('Neuromag_122', path = './')

# forward modeling
source_space_method = 'ico5'

# source reconstruction
use_calm_cov = False
method = 'dSPM'
mne_evoked_time = [0.050, 0.100, 0.200] # s
stc_animation = [0,0.5] # s
eeg_fwd = False
parcellation = 'aparc.a2009s'

# Dipole-fit
ECDs = {}


ECD_min = 0.200
ECD_max = 0.250

target_labels = ['G_postcentral-lh', 'S_postcentral-lh',
                 'S_circular_insula_sup-lh', 'G_Ins_lg&S_cent_ins-lh',
                 'S_circular_insula_inf-lh', 'G&S_cingul-Ant-lh']

# morph maps
morph_to='fsaverage'
vertices_to = [np.arange(10242), np.arange(10242)]

# grand averages
# empty containers to the put the single subjects data in
ga_conditions = ['ER']

# statistics
independent_variable_1 = 'standard_3'
independent_variable_2 = 'non_stimulation'
time_window = (0.050, 0.060)
n_permutations = 10000 # specify as integer

# statistics plotting
p_threshold = 1e-15 # 1e-15 is the smallest it can get for the way it is coded

# freesurfer and MNE-C commands
n_jobs_freesurfer = 4 # change according to amount of processors you have
                        # available
 # supply a method and a spacing/grade
                                  # see mne_setup_source_space --help in bash
                                  # methods 'spacing', 'ico', 'oct'

#parameters_stop
#==============================================================================
# PATHS
#%%============================================================================
if sys.platform == 'win32':
    home_path = 'Z:/Promotion' # change this according to needs

if sys.platform == 'linux':
    home_path = '/mnt/z/Promotion' # change this according to needs

project_name = 'Pin-Prick-Projekt/PP_Messungen'
data_path = join(home_path, project_name, 'Daten')
sub_script_path = join(data_path, '_Subject_scripts')
subjects_dir = join(home_path, 'Freesurfer/Output')
mne.utils.set_config("SUBJECTS_DIR", subjects_dir, set_env=True)
save_dir_averages = join(data_path,'grand_averages')

if exec_ops['erm_analysis'] or exec_ops['motor_erm_analysis']:
    figures_path = join(home_path, project_name, 'Figures/ERM_Figures')    
else:
    figures_path = join(home_path, project_name, 'Figures/')

#add subjects, mri_subjects, sub_dict, bad_channels_dict
sub_list_path = join(sub_script_path, 'sub_list.py')
erm_list_path = join(sub_script_path, 'erm_list.py')
motor_erm_list_path = join(sub_script_path, 'motor_erm_list.py')
mri_sub_list_path = join(sub_script_path, 'mri_sub_list.py')
sub_dict_path = join(sub_script_path, 'sub_dict.py')
erm_dict_path = join(sub_script_path, 'erm_dict.py')
bad_channels_dict_path = join(sub_script_path, 'bad_channels_dict.py')
sub_cond_dict_path = join(sub_script_path, 'sub_cond_dict.py')

#==============================================================================
# SUBJECT ORGANISATION
#%%============================================================================
orig_data_path = join(home_path, 'Pin-Prick-Projekt/Messungen_Dateien')
orig_mri_data_path = join(home_path, 'Freesurfer/Output')

if exec_ops['add_subjects']: # set 1 to run
    suborg.add_subjects(sub_list_path, erm_list_path, motor_erm_list_path,
                        home_path, project_name, data_path, figures_path,
                        subjects_dir, orig_data_path, gui=False)

if exec_ops['add_mri_subjects']: # set 1 to run
    suborg.add_mri_subjects(mri_sub_list_path, data_path)

if exec_ops['add_sub_dict']: # set 1 to run
    suborg.add_sub_dict(sub_dict_path, sub_list_path, data_path)

if exec_ops['add_erm_dict']: #set 1 to run
    suborg.add_erm_dict(erm_dict_path, sub_list_path, data_path)

if exec_ops['add_bad_channels']:
    suborg.add_bad_channels_dict(bad_channels_dict_path, sub_list_path,
                                 erm_list_path, motor_erm_list_path,
                                 data_path, predefined_bads,
                                 sub_script_path)

if 0:
    suborg.add_sub_cond_dict(sub_cond_dict_path, sub_list_path, data_path)

#Functions

all_subjects = suborg.read_subjects(sub_list_path)
all_mri_subjects = suborg.read_mri_subjects(mri_sub_list_path)
erm_files = suborg.read_subjects(erm_list_path)
motor_erm_files = suborg.read_subjects(motor_erm_list_path)
sub_to_mri = suborg.read_sub_dict(sub_dict_path)
erm_dict = suborg.read_sub_dict(erm_dict_path) # add None if not available
bad_channels_dict = suborg.read_bad_channels_dict(bad_channels_dict_path)
sub_cond_dict = suborg.read_sub_cond_dict(sub_cond_dict_path)

#==========================================================================
# MRI-Subjects
#==========================================================================
if exec_ops['mri_preprocessing']:

    mri_subjects = suborg.mri_subject_selection(which_mri_subject, all_mri_subjects)

    print('Selected MRI-Subjects:')
    for i in mri_subjects:
        print(i)

    for mri_subject in mri_subjects:
        print('='*60 + '\n', mri_subject)

        #==========================================================================
        # BASH SCRIPTS
        #==========================================================================
        if exec_ops['segment_mri']:
            op.segment_mri(mri_subject, subjects_dir, n_jobs_freesurfer)

        if exec_ops['apply_watershed']:
            op.apply_watershed(mri_subject, subjects_dir, overwrite)

        if exec_ops['make_dense_scalp_surfaces']:
            op.make_dense_scalp_surfaces(mri_subject, subjects_dir, overwrite)

        #==========================================================================
        # Forward Modeling
        #==========================================================================
        if exec_ops['setup_source_space']:
            op.setup_source_space(mri_subject, subjects_dir, source_space_method,
                           overwrite, n_jobs)
        
        if exec_ops['prepare_bem']:
            op.prepare_bem(mri_subject, subjects_dir, overwrite)
            
        #==========================================================================
        # PLOT SOURCE SPACES
        #==========================================================================

        if exec_ops['plot_source_space']:
            plot.plot_source_space(mri_subject, subjects_dir, source_space_method, save_plots, figures_path)

        if exec_ops['plot_bem']:
            plot.plot_bem(mri_subject, subjects_dir, source_space_method, figures_path,
                          save_plots)
            
        if exec_ops['plot_labels']:
            plot.plot_labels(mri_subject, subjects_dir, save_plots, figures_path,
                             parcellation)
            
        # close plots
        if exec_ops['close_plots']:
            plot.close_all()
#==========================================================================
# Subjects
#=========================================================================

if exec_ops['erm_analysis']:
    subjects = suborg.file_selection(which_erm_file, erm_files)   

if exec_ops['motor_erm_analysis']:
    subjects = suborg.file_selection(which_motor_erm_file, motor_erm_files)

else:
    subjects = suborg.file_selection(which_file, all_subjects)

print('Selected Subjects:')
for i in subjects:
    print(i)

evoked_data_all = dict(pinprick=[], WU_First=[], WU_Last=[])
morphed_data_all = dict(pinprick=[], WU_First=[], WU_Last=[])


for subject in subjects:
    name = subject #changed for Kopfklinik-naming-convention
    subject_index = subjects.index(subject)
    
    if exec_ops['erm_analysis'] or exec_ops['motor_erm_analysis']:
        save_dir = join(data_path, 'empty_room_data')
        
    else:
        save_dir = join(data_path, name)       
    
    pattern = r'pp[0-9]+[a-z]?'
    
    match = re.match(pattern, subject)
    prefix = match.group()
    
    ermsub = prefix + '_leer'
    subtomri = sub_to_mri[prefix]
            
    try:
        bad_channels = bad_channels_dict[subject]
    except KeyError as k:
        print(f'No bad channels for {k}')
        suborg.add_bad_channels_dict(bad_channels_dict_path, sub_list_path,
                                     erm_list_path, motor_erm_list_path,
                                     data_path, predefined_bads)

    event_id_list = []

    # Print Subject Console Header
    print(60*'='+'\n'+name)

    #==========================================================================
    # POPULATE SUBJECT DIRECTORIES
    #==========================================================================
    if not exec_ops['erm_analysis'] and not exec_ops['motor_erm_analysis']:
        if exec_ops['populate_data_directory']:
            op.populate_data_directory(home_path, project_name, data_path,
                                       figures_path, subjects_dir, subjects,
                                       event_id)

    #==========================================================================
    # FILTER RAW
    #==========================================================================

    if exec_ops['filter_raw']:
        op.filter_raw(name, save_dir, lowpass, highpass, overwrite, ermsub,
                              data_path, n_jobs, enable_cuda, bad_channels)

    #==========================================================================
    # FIND EVENTS
    #==========================================================================

    if exec_ops['find_events']:
        op.find_events(name, save_dir, min_duration,
                adjust_timeline_by_msec,lowpass, highpass, overwrite)

    if exec_ops['find_eog_events']:
        op.find_eog_events(name, save_dir, eog_channel)

    #==========================================================================
    # EPOCHS
    #==========================================================================

    if exec_ops['epoch_raw']:
        op.epoch_raw(name, save_dir,lowpass, highpass, event_id, tmin,
                     tmax, baseline, reject, flat, autoreject, overwrite_ar,
                     reject_eog_epochs, overwrite)

    #==========================================================================
    # SIGNAL SPACE PROJECTION
    #==========================================================================
    if exec_ops['run_ssp_er']:
        op.run_ssp_er(name, save_dir, lowpass, highpass, data_path, ermsub, bad_channels,
                      eog_channel, ecg_channel, overwrite)

    if exec_ops['apply_ssp_er']:
        op.apply_ssp_er(name, save_dir,lowpass, highpass, overwrite)

    if exec_ops['run_ssp_clm']:
        op.run_ssp_clm(name, save_dir, lowpass, highpass, bad_channels, overwrite)

    if exec_ops['apply_ssp_clm']:
        op.apply_ssp_clm(name, save_dir, lowpass, highpass, overwrite)

    if exec_ops['run_ssp_eog']:
        op.run_ssp_eog(name, save_dir, lowpass, highpass, n_jobs, eog_channel,
                                   bad_channels, overwrite)

    if exec_ops['apply_ssp_eog']:
        op.apply_ssp_eog(name, save_dir, lowpass, highpass, overwrite)

    if exec_ops['run_ssp_ecg']:
        op.run_ssp_ecg(name, save_dir,lowpass, highpass, n_jobs, ecg_channel,
                                   bad_channels, overwrite)

    if exec_ops['apply_ssp_ecg']:
        op.apply_ssp_ecg(name, save_dir,lowpass, highpass, overwrite)

    if exec_ops['plot_ssp']:
        plot.plot_ssp(name, save_dir,lowpass, highpass, subject, save_plots,
                      figures_path, bad_channels, layout, ermsub)

    if exec_ops['plot_ssp_eog']:
        plot.plot_ssp_eog(name, save_dir,lowpass, highpass, subject, save_plots,
                              figures_path, bad_channels, layout)

    if exec_ops['ica_pure']:
        op.ica_pure(name, save_dir,lowpass, highpass, overwrite, eog_channel,
                            ecg_channel, layout, reject, flat, bad_channels, autoreject,
                            overwrite_ar)

    if exec_ops['run_ica']:
        op.run_ica(name, save_dir,lowpass, highpass, eog_channel, ecg_channel,
                           reject, flat, bad_channels, overwrite, autoreject,
                           save_plots, figures_path, sub_script_path,
                           exec_ops['erm_analysis'])

    #==========================================================================
    # LOAD NON-ICA'ED EPOCHS AND APPLY ICA
    #==========================================================================

    if exec_ops['apply_ica']:
        op.apply_ica(name, save_dir,lowpass, highpass, data_path, overwrite)

    #==========================================================================
    # EVOKEDS
    #==========================================================================

    if exec_ops['get_evokeds']:
        op.get_evokeds(name, save_dir,lowpass, highpass, exec_ops, ermsub,
                               detrend, overwrite)

    #==========================================================================
    # TIME-FREQUENCY-ANALASYS
    #==========================================================================

    if exec_ops['TF_Morlet']:
        op.TF_Morlet(name, save_dir,lowpass, highpass, TF_Morlet_Freqs, decim, n_jobs)

    #==========================================================================
    # NOISE COVARIANCE MATRIX
    #==========================================================================

    if exec_ops['estimate_noise_covariance']:
        op.estimate_noise_covariance(name, save_dir,lowpass, highpass, overwrite,
                                     ermsub, data_path, bad_channels, n_jobs,
                                     use_calm_cov)

    if exec_ops['plot_noise_covariance']:
        plot.plot_noise_covariance(name, save_dir,lowpass, highpass, subject,
                                   subtomri, save_plots, figures_path, ermsub,
                                   use_calm_cov)

    #==========================================================================
    # CO-REGISTRATION
    #==========================================================================

    # use mne.gui.coregistration()

    if exec_ops['mri_coreg']:
        op.mri_coreg(name, save_dir, subtomri, subjects_dir)

    if exec_ops['plot_transformation']:
        plot.plot_transformation(name, save_dir, subtomri, subjects_dir,
                                 save_plots, figures_path)

    #==========================================================================
    # CREATE FORWARD MODEL
    #==========================================================================

    if exec_ops['create_forward_solution']:
        op.create_forward_solution(name, save_dir, subtomri, subjects_dir,
                                           source_space_method, overwrite,
                                           n_jobs, eeg_fwd)

    #==========================================================================
    # CREATE INVERSE OPERATOR
    #==========================================================================

    if exec_ops['create_inverse_operator']:
        op.create_inverse_operator(name, save_dir,lowpass, highpass,
                                        overwrite, ermsub, use_calm_cov)

    #==========================================================================
    # SOURCE ESTIMATE MNE
    #==========================================================================

    if exec_ops['source_estimate']:
        op.source_estimate(name, save_dir,lowpass, highpass, method, overwrite)

    if exec_ops['vector_source_estimate']:
        op.vector_source_estimate(name, save_dir,lowpass, highpass, method, overwrite)

    if exec_ops['ECD_fit']:
        op.ECD_fit(name, save_dir,lowpass, highpass, ermsub, subject, subjects_dir,
                           subtomri, source_space_method, use_calm_cov, ECDs,
                           n_jobs, target_labels, save_plots, figures_path)

    #==========================================================================
    # PRINT INFO
    #==========================================================================
    if exec_ops['print_info']:
        plot.print_info(name, save_dir, save_plots)

    if exec_ops['plot_sensors']:
        plot.plot_sensors(name, save_dir)

    #==========================================================================
    # PLOT RAW DATA
    #==========================================================================

    if exec_ops['plot_raw']:
        plot.plot_raw(name, save_dir, overwrite, bad_channels, bad_channels_dict)

    if exec_ops['plot_filtered']:
        plot.plot_filtered(name, save_dir, lowpass, highpass, bad_channels)

    if exec_ops['plot_events']:
        plot.plot_events(name, save_dir, save_plots, figures_path, event_id)

    if exec_ops['plot_events_diff']:
        plot.plot_events_diff(name, save_dir, save_plots, figures_path)

    if exec_ops['plot_eog_events']:
        plot.plot_eog_events(name, save_dir)

    #==========================================================================
    # PLOT POWER SPECTRA
    #==========================================================================

    if exec_ops['plot_power_spectra']:
        plot.plot_power_spectra(name, save_dir,lowpass, highpass, subject,
                                save_plots, figures_path, bad_channels)

    if exec_ops['plot_power_spectra_epochs']:
        plot.plot_power_spectra_epochs(name, save_dir,lowpass, highpass, subject,
                                       save_plots, figures_path, bad_channels)

    if exec_ops['plot_power_spectra_topo']:
        plot.plot_power_spectra_topo(name, save_dir,lowpass, highpass, subject,
                                     save_plots, figures_path, bad_channels, layout)

    #==========================================================================
    # PLOT CLEANED EPOCHS
    #==========================================================================
    if exec_ops['plot_epochs']:
        plot.plot_epochs(name, save_dir,lowpass, highpass, subject, save_plots,
                               figures_path)

    if exec_ops['plot_epochs_image']:
        plot.plot_epochs_image(name, save_dir,lowpass, highpass, subject, save_plots,
                               figures_path)

    if exec_ops['plot_epochs_topo']:
        plot.plot_epochs_topo(name, save_dir,lowpass, highpass, subject, save_plots,
                      figures_path, layout)

    #==========================================================================
    # PLOT EVOKEDS
    #==========================================================================

    if exec_ops['plot_evoked_topo']:
        plot.plot_evoked_topo(name, save_dir,lowpass, highpass, subject, save_plots,
                              figures_path)

    if exec_ops['plot_evoked_topomap']:
        plot.plot_evoked_topomap(name, save_dir,lowpass, highpass, subject, save_plots,
                                 figures_path, layout)

    if exec_ops['plot_butterfly_evokeds']:
        plot.plot_butterfly_evokeds(name, save_dir,lowpass, highpass, subject,
                                    save_plots, figures_path,
                                    time_unit, ermsub, use_calm_cov)

    if exec_ops['plot_evoked_field']:
        plot.plot_evoked_field(name, save_dir,lowpass, highpass, subject, subtomri,
                               subjects_dir, save_plots, figures_path,
                               mne_evoked_time, n_jobs)

    if exec_ops['plot_evoked_joint']:
        plot.plot_evoked_joint(name, save_dir,lowpass, highpass, subject, save_plots,
                               layout, figures_path, ECDs)

    if exec_ops['plot_evoked_white']:
        plot.plot_evoked_white(name, save_dir,lowpass, highpass, subject,
                               save_plots, figures_path, ermsub, use_calm_cov)

    if exec_ops['plot_evoked_image']:
        plot.plot_evoked_image(name, save_dir,lowpass, highpass, subject,
                               save_plots, figures_path)

    if exec_ops['animate_topomap']:
        plot.animate_topmap()

    #==========================================================================
    # PLOT SOURCE ESTIMATES MNE
    #==========================================================================

    if exec_ops['plot_source_estimates']:
        plot.plot_source_estimates(name, save_dir,lowpass, highpass,
                                      subtomri, subjects_dir, subject,
                                      method, mne_evoked_time,
                                      save_plots, figures_path)

    if exec_ops['plot_vector_source_estimates']:
        plot.plot_vector_source_estimates(name, save_dir,lowpass, highpass,
                                      subtomri, subjects_dir, subject,
                                      method, mne_evoked_time,
                                      save_plots, figures_path)

    if exec_ops['plot_animated_stc']:
        plot.plot_animated_stc(name, save_dir,lowpass, highpass, subtomri,
                               subjects_dir, subject, method, mne_evoked_time,
                               stc_animation, tmin, tmax, save_plots, figures_path)

    if exec_ops['plot_snr']:
        plot.plot_snr(name, save_dir,lowpass, highpass, save_plots, figures_path)

    if exec_ops['label_time_course']:
        plot.label_time_course(name, save_dir, lowpass, highpass, subtomri,
                               target_labels, save_plots, figures_path,
                               parcellation)
    
    #==========================================================================
    # MORPH TO FSAVERAGE
    #==========================================================================

    if exec_ops['morph_to_fsaverage']:
        stcs = op.morph_data_to_fsaverage(name, save_dir,lowpass, highpass,
                                        subjects_dir, subject, subtomri,
                                        method,
                                        overwrite, n_jobs, vertices_to, morph_to)


    if exec_ops['morph_to_fsaverage_precomputed']:
        stcs = op.morph_data_to_fsaverage_precomputed(name, save_dir,lowpass, highpass, subjects_dir, subject,
                                                              subtomri, method, overwrite, n_jobs, morph_to, vertices_to)

    #==========================================================================
    # GRAND AVERAGE EVOKEDS (within-subject part)
    #==========================================================================

    if exec_ops['grand_averages_evokeds']:
        evoked_data = io.read_evokeds(name, save_dir, lowpass, highpass)
        for evoked in evoked_data:
            trial_type = evoked.comment
            evoked_data_all[trial_type].append(evoked)

    #==========================================================================
    # GRAND AVERAGE MORPHED DATA (within-subject part)
    #==========================================================================

    if exec_ops['average_morphed_data'] or \
        exec_ops['statistics_source_space']:
        morphed_data = io.read_avg_source_estimates(name, save_dir,lowpass, highpass,
                                                    method)
        for trial_type in morphed_data:
            morphed_data_all[trial_type].append(morphed_data[trial_type])

    #==========================================================================
    # General Statistics
    #==========================================================================
    if exec_ops['corr_ntr']:
        op.corr_ntr(name, save_dir, lowpass, highpass, exec_ops,
                    ermsub, subtomri, save_plots, figures_path)
        
    if exec_ops['avg_ntr']:
        op.avg_ntr(name, save_dir, lowpass, highpass, bad_channels, event_id,
                            tmin, tmax, baseline, figures_path, save_plots, autoreject,
                            overwrite_ar, reject, flat)

    # close all plots
    if exec_ops['close_plots']:
        plot.close_all()

# GOING OUT OF SUBJECT LOOP (FOR AVERAGES)

#==============================================================================
# GRAND AVERAGES (sensor space and source space)
#==============================================================================

if exec_ops['grand_averages_evokeds']:
    op.grand_average_evokeds(evoked_data_all, save_dir_averages,
                                    lowpass, highpass, which_file)

if exec_ops['average_morphed_data']:
    op.average_morphed_data(morphed_data_all, method,
                                 save_dir_averages,lowpass, highpass, which_file)

#==============================================================================
# GRAND AVERAGES PLOTS (sensor space and source space)
#==============================================================================

if exec_ops['plot_grand_averages_evokeds']:
    plot.plot_grand_average_evokeds(name,lowpass, highpass, save_dir_averages,
                                    evoked_data_all, event_id_list,
                                    save_plots, figures_path, which_file)

if exec_ops['plot_grand_averages_butterfly_evokeds']:
    plot.plot_grand_averages_butterfly_evokeds(name,lowpass, highpass, save_dir_averages,
                                               event_id_list, save_plots, figures_path,
                                               which_file)

if exec_ops['plot_grand_averages_source_estimates']:
    plot.plot_grand_averages_source_estimates(name, save_dir_averages,lowpass, highpass,
                                              subjects_dir, method,
                                              mne_evoked_time, event_id_list, save_plots,
                                              figures_path, which_file)

if exec_ops['label_time_course_avg']:
    plot.label_time_course_avg(morphed_data_all, save_dir_averages,lowpass, highpass, method,
                      which_file, subjects_dir, source_space_method,
                      target_labels, save_plots, event_id_list, figures_path)
#==============================================================================
# STATISTICS SOURCE SPACE
#==============================================================================

if exec_ops['statistics_source_space']:
    op.statistics_source_space(morphed_data_all, save_dir_averages,
                                       independent_variable_1,
                                       independent_variable_2,
                                       time_window, n_permutations,lowpass, highpass,
                                       overwrite)

#==============================================================================
# PLOT GRAND AVERAGES OF SOURCE ESTIMATES WITH STATISTICS CLUSTER MASK
#==============================================================================

if exec_ops['plot_grand_averages_source_estimates_cluster_masked']:
    plot.plot_grand_averages_source_estimates_cluster_masked(
        name, save_dir_averages,lowpass, highpass, subjects_dir, method, time_window,
        save_plots, figures_path, independent_variable_1,
        independent_variable_2, mne_evoked_time, p_threshold)
