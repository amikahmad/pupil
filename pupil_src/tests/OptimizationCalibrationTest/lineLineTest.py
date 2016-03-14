import os, sys, platform
loc = os.path.abspath(__file__).rsplit('pupil_src', 1)
sys.path.append(os.path.join(loc[0], 'pupil_src', 'shared_modules'))

from calibration_routines.optimization_calibration import  bundle_adjust_calibration

import numpy as np
import cv2
import math
import math_helper
from numpy import array, cross, dot, double, hypot, zeros
from math import acos, atan2, cos, pi, sin, radians
from calibration_routines.visualizer_calibration import *
from calibration_routines.calibrate import find_rigid_transform

def show_result(observers,points, name = "Calibration"):

    rotation = np.array(observers[1]['rotation'])
    translation = np.array(observers[1]['translation'])

    print 'rotation: ' , math_helper.about_axis_from_quaternion(rotation), 'thruth:',math_helper.about_axis_from_quaternion(cam2_rotation_quaternion)
    print 'translation: ' , translation, 'thruth:',cam2_center

    return
    #replace with the optimized rotation and translation
    R = math_helper.quaternion_rotation_matrix(rotation)
    cam2_transformation_matrix  = np.matrix(np.eye(4))
    cam2_transformation_matrix[:3,:3] = R
    t = np.matrix(translation)
    t.shape = (3,1)
    cam2_transformation_matrix[:3,3:4] = t

    def toWorld(p):
        return np.dot(R, p)+t

    eye = { 'center': translation, 'radius': 1.0}

    intersection_points_a = [] #world coords
    intersection_points_b = [] #cam2 coords
    avg_error = 0.0
    for a,b in zip(cam1_points , cam2_points): #world coords , cam2 coords

        line_a = (np.array(cam1_center) , np.array(a))
        line_b = (toWorld(cam1_center) , toWorld(b) ) #convert to world for intersection

        ai, bi, distance =  math_helper.nearest_intersection_points( line_a , line_b ) #world coords
        avg_error +=distance
        intersection_points_a.append(ai)
        intersection_points_b.append(bi)  #cam2 coords , since visualizer expects local coordinates

    avg_error /= len(cam2_points)
    print 'avg distace of intersections re calulated on scaled data: ', avg_error

    #cam2_points_world = [toWorld(p) for p in cam2_points]

    visualizer = Calibration_Visualizer(None,None, intersection_points_a ,cam2_transformation_matrix , intersection_points_b, run_independently = True , name = name)
    visualizer.open_window()
    while visualizer.window:
        visualizer.update_window( None, [] , eye)

    return

if __name__ == '__main__':


    from random import uniform

    cam1_center  = (0,0,0)
    cam1_rotation_angle_axis   = [0 , (0.0,1.0,0.0) ]
    cam1_rotation_quaternion = math_helper.quaternion_about_axis( cam1_rotation_angle_axis[0] , cam1_rotation_angle_axis[1])
    cam1_rotation_matrix = math_helper.quaternion_rotation_matrix(cam1_rotation_quaternion)

    cam2_center  = np.array((4,-30,30))
    cam2_rotation_angle_axis   = [ -np.pi* 0.9, (0.0,1.0,0.0) ]
    cam2_rotation_quaternion = math_helper.quaternion_about_axis( cam2_rotation_angle_axis[0] , cam2_rotation_angle_axis[1])
    cam2_rotation_matrix = math_helper.quaternion_rotation_matrix(cam2_rotation_quaternion)
    random_points = []
    random_points_amount = 80

    x_var = 200
    y_var = 200
    z_var = 500
    z_min = 200
    for i in range(0,random_points_amount):
        random_point = ( uniform(-x_var,x_var) ,  uniform(-y_var,y_var) ,  uniform(z_min,z_min+z_var)  )
        random_points.append(random_point)


    def toEye(p):
        return np.dot(cam2_rotation_matrix.T, p-cam2_center )

    cam1_points = [] #cam1 coords
    cam2_points = [] #cam2 coords
    for p in random_points:
        cam1_points.append(p)
        noise = 0 #randomize point in eye space
        pr = p + np.array( (uniform(-noise,+noise),uniform(-noise,+noise),uniform(-noise,+noise))  )
        p2 = toEye(pr) # to cam2 coordinate system
        # p2 *= 1.2,1.3,1.0
        cam2_points.append(p2)


    cam1_observation = [ p/np.linalg.norm(p) for p in cam1_points]
    cam2_observation = [ p/np.linalg.norm(p) for p in cam2_points]

    initial_R,initial_t = find_rigid_transform(np.array(cam2_observation),np.array(cam1_observation))
    initial_rotation_quaternion = math_helper.quaternion_from_rotation_matrix(initial_R)
    initial_translation = np.array(initial_t).reshape(3)
    initial_translation *= np.linalg.norm(cam2_center)/np.linalg.norm(initial_translation)


    o1 = { "observations" : cam1_observation , "translation" : [0,0,0] , "rotation" : cam1_rotation_quaternion  }
    o2 = { "observations" : cam2_observation , "translation" : initial_translation , "rotation" : initial_rotation_quaternion  }
    initial_observers = [o1, o2]

    # initial_points = np.ones(np.array(cam1_points).shape,dtype= np.array(cam1_points).dtype)
    initial_points = np.array(cam1_observation)*500


    success, observers, points = bundle_adjust_calibration( initial_observers , initial_points, fix_translation = False )


    #bundle adjustment does not solve global scale we add this from the ground thruth here:
    scaled_points = []
    avg_scale = 0
    for a,b in zip(cam1_points, points):
        scale = np.linalg.norm(np.array(a))/np.linalg.norm(np.array(b))
        scaled_points.append(np.array(b)*scale)
        avg_scale += scale
        # print a,np.array(b)*scale,scale

    avg_scale /= len(cam1_points)
    # print avg_scale
    for o in observers:
        o['translation'] = np.array(o['translation'])*avg_scale


    from multiprocessing import Process
    print "final result -------------------"
    p = Process(target=show_result, args=(observers, points))
    p.start();

    import time
    time.sleep(1)
    print "inital guess -------------------"
    show_result(initial_observers,initial_points, "inital guess")

    p.join()

