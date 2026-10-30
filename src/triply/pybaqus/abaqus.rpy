# -*- coding: mbcs -*-
#
# Abaqus/CAE Release 2024 replay file
# Internal Version: 2023_09_21-14.55.25 RELr426 190762
# Run by cofo on Fri Oct 23 14:51:05 2026
#

# from driverUtils import executeOnCaeGraphicsStartup
# executeOnCaeGraphicsStartup()
#: Executing "onCaeGraphicsStartup()" in the site directory ...
from abaqus import *
from abaqusConstants import *
session.Viewport(name='Viewport: 1', origin=(0.0, 0.0), width=206.384750366211, 
    height=228.433334350586)
session.viewports['Viewport: 1'].makeCurrent()
session.viewports['Viewport: 1'].maximize()
from caeModules import *
from driverUtils import executeOnCaeStartup
executeOnCaeStartup()
session.viewports['Viewport: 1'].partDisplay.geometryOptions.setValues(
    referenceRepresentation=ON)
Mdb()
#: A new model database has been created.
#: The model "Model-1" has been created.
session.viewports['Viewport: 1'].setValues(displayedObject=None)
s = mdb.models['Model-1'].ConstrainedSketch(name='__profile__', 
    sheetSize=200.0)
g, v, d, c = s.geometry, s.vertices, s.dimensions, s.constraints
s.setPrimaryObject(option=STANDALONE)
s.rectangle(point1=(0.0, 0.0), point2=(41.25, 28.75))
s.ObliqueDimension(vertex1=v[0], vertex2=v[1], textPoint=(-10.3119506835938, 
    15.96875), value=10.0)
s.ObliqueDimension(vertex1=v[3], vertex2=v[0], textPoint=(29.2596969604492, 
    9.69791793823242), value=10.0)
p = mdb.models['Model-1'].Part(name='Part-1', dimensionality=THREE_D, 
    type=DEFORMABLE_BODY)
p = mdb.models['Model-1'].parts['Part-1']
p.BaseSolidExtrude(sketch=s, depth=10.0)
s.unsetPrimaryObject()
p = mdb.models['Model-1'].parts['Part-1']
session.viewports['Viewport: 1'].setValues(displayedObject=p)
del mdb.models['Model-1'].sketches['__profile__']
session.viewports['Viewport: 1'].view.setValues(nearPlane=24.8935, 
    farPlane=48.2773, width=35.6231, height=16.2244, viewOffsetX=3.66909, 
    viewOffsetY=0.437525)
session.viewports['Viewport: 1'].view.setValues(nearPlane=20.9174, 
    farPlane=42.1704, width=29.9333, height=13.633, cameraPosition=(-11.6584, 
    11.5014, 29.3909), cameraUpVector=(-0.327339, 0.896863, -0.297466), 
    cameraTarget=(5.16761, 20.929, -1.69762), viewOffsetX=3.08305, 
    viewOffsetY=0.367642)
session.viewports['Viewport: 1'].view.setValues(nearPlane=20.0753, 
    farPlane=41.2494, width=28.7282, height=13.0842, cameraPosition=(12.0002, 
    44.6504, 26.8034), cameraUpVector=(-0.564189, 0.373772, -0.736196), 
    cameraTarget=(0.891961, 17.4855, 4.95927), viewOffsetX=2.95893, 
    viewOffsetY=0.352841)
session.viewports['Viewport: 1'].view.setValues(nearPlane=21.863, 
    farPlane=42.181, width=31.2865, height=14.2493, cameraPosition=(20.8162, 
    17.74, 32.4577), cameraUpVector=(0.272873, 0.882203, -0.383742), 
    cameraTarget=(-0.514263, 25.7048, 3.82097), viewOffsetX=3.22242, 
    viewOffsetY=0.384261)
session.viewports['Viewport: 1'].view.setValues(nearPlane=22.3999, 
    farPlane=42.3241, width=32.0548, height=14.5992, cameraPosition=(32.4715, 
    18.4121, 21.6952), cameraUpVector=(0.0838868, 0.823005, -0.561805), 
    cameraTarget=(0.0906625, 26.1896, 6.54657), viewOffsetX=3.30155, 
    viewOffsetY=0.393698)
session.viewports['Viewport: 1'].view.setValues(nearPlane=22.2591, 
    farPlane=41.2703, width=31.8533, height=14.5075, cameraPosition=(16.3995, 
    25.1965, 34.921), cameraUpVector=(-0.00492853, 0.902515, -0.430631), 
    cameraTarget=(-1.04946, 23.2972, 2.82093), viewOffsetX=3.2808, 
    viewOffsetY=0.391224)
session.viewports['Viewport: 1'].view.setValues(nearPlane=20.8808, 
    farPlane=41.9706, width=29.881, height=13.6092, cameraPosition=(10.9998, 
    38.1885, 32.612), cameraUpVector=(-0.252375, 0.659971, -0.707634), 
    cameraTarget=(-0.419073, 20.3286, 2.79386), viewOffsetX=3.07765, 
    viewOffsetY=0.366999)
session.viewports['Viewport: 1'].view.setValues(nearPlane=20.4765, 
    farPlane=42.3676, width=29.3025, height=13.3457, cameraPosition=(19.9634, 
    44.3075, 23.9762), cameraUpVector=(-0.439452, 0.467518, -0.767013), 
    cameraTarget=(-0.958431, 20.5782, 5.59991), viewOffsetX=3.01806, 
    viewOffsetY=0.359893)
session.viewports['Viewport: 1'].view.setValues(nearPlane=20.5606, 
    farPlane=42.1233, width=29.4229, height=13.4005, cameraPosition=(15.4604, 
    45.5615, 25.41), cameraUpVector=(-0.428523, 0.42465, -0.797521), 
    cameraTarget=(-0.576777, 19.7749, 5.00532), viewOffsetX=3.03046, 
    viewOffsetY=0.361371)
session.viewports['Viewport: 1'].partDisplay.setValues(sectionAssignments=ON, 
    engineeringFeatures=ON)
session.viewports['Viewport: 1'].partDisplay.geometryOptions.setValues(
    referenceRepresentation=OFF)
mdb.models['Model-1'].Material(name='Material-1')
mdb.models['Model-1'].materials['Material-1'].Elastic(table=((200000.0, 0.3), 
    ))
mdb.models['Model-1'].HomogeneousSolidSection(name='Section-1', 
    material='Material-1', thickness=None)
p = mdb.models['Model-1'].parts['Part-1']
c = p.cells
cells = c.getSequenceFromMask(mask=('[#1 ]', ), )
region = p.Set(cells=cells, name='Set-1')
p = mdb.models['Model-1'].parts['Part-1']
p.SectionAssignment(region=region, sectionName='Section-1', offset=0.0, 
    offsetType=MIDDLE_SURFACE, offsetField='', 
    thicknessAssignment=FROM_SECTION)
a = mdb.models['Model-1'].rootAssembly
session.viewports['Viewport: 1'].setValues(displayedObject=a)
session.viewports['Viewport: 1'].assemblyDisplay.setValues(
    optimizationTasks=OFF, geometricRestrictions=OFF, stopConditions=OFF)
a = mdb.models['Model-1'].rootAssembly
a.DatumCsysByDefault(CARTESIAN)
p = mdb.models['Model-1'].parts['Part-1']
a.Instance(name='Part-1-1', part=p, dependent=ON)
session.viewports['Viewport: 1'].assemblyDisplay.setValues(
    adaptiveMeshConstraints=ON)
mdb.models['Model-1'].StaticStep(name='Step-1', previous='Initial')
session.viewports['Viewport: 1'].assemblyDisplay.setValues(step='Step-1')
session.viewports['Viewport: 1'].assemblyDisplay.setValues(interactions=ON, 
    constraints=ON, connectors=ON, engineeringFeatures=ON, 
    adaptiveMeshConstraints=OFF)
session.viewports['Viewport: 1'].view.setValues(nearPlane=47.0544, 
    farPlane=84.9575, width=64.2147, height=29.2463, viewOffsetX=2.17231, 
    viewOffsetY=0.509374)
session.viewports['Viewport: 1'].view.setValues(nearPlane=51.0615, 
    farPlane=77.1438, width=69.6832, height=31.7369, cameraPosition=(22.6576, 
    23.5577, 65.9433), cameraUpVector=(-0.0748727, 0.888675, -0.452383), 
    cameraTarget=(3.72985, 14.8392, 3.31336), viewOffsetX=2.3573, 
    viewOffsetY=0.552752)
session.viewports['Viewport: 1'].view.setValues(nearPlane=49.9075, 
    farPlane=76.2936, width=68.1083, height=31.0197, cameraPosition=(-7.53365, 
    24.3987, 66.0426), cameraUpVector=(0.173476, 0.88092, -0.440325), 
    cameraTarget=(4.50111, 14.9134, 1.83995), viewOffsetX=2.30402, 
    viewOffsetY=0.54026)
session.viewports['Viewport: 1'].view.setValues(nearPlane=47.9502, 
    farPlane=76.6936, width=65.4372, height=29.8031, cameraPosition=(-32.4033, 
    24.8875, 53.7591), cameraUpVector=(0.347902, 0.877523, -0.330028), 
    cameraTarget=(6.16667, 14.8787, 1.13814), viewOffsetX=2.21366, 
    viewOffsetY=0.519071)
session.viewports['Viewport: 1'].view.setValues(nearPlane=47.4815, 
    farPlane=75.5186, width=64.7976, height=29.5118, cameraPosition=(-53.0075, 
    27.5417, 20.7659), cameraUpVector=(0.506176, 0.857614, -0.0910175), 
    cameraTarget=(8.92906, 14.6432, 1.94386), viewOffsetX=2.19202, 
    viewOffsetY=0.513997)
session.viewports['Viewport: 1'].view.setValues(nearPlane=49.6404, 
    farPlane=72.4172, width=67.7438, height=30.8537, cameraPosition=(-55.6301, 
    21.4107, 2.96084), cameraUpVector=(0.421643, 0.904431, 0.0649836), 
    cameraTarget=(10.0731, 15.0982, 3.08322), viewOffsetX=2.29169, 
    viewOffsetY=0.537367)
session.viewports['Viewport: 1'].view.setValues(nearPlane=46.5527, 
    farPlane=74.6554, width=63.5301, height=28.9346, cameraPosition=(-53.9283, 
    1.28886, 10.8383), cameraUpVector=(0.111946, 0.992054, 0.0574272), 
    cameraTarget=(9.68443, 16.7746, 2.44879), viewOffsetX=2.14914, 
    viewOffsetY=0.503942)
session.viewports['Viewport: 1'].view.setValues(nearPlane=43.3463, 
    farPlane=77.3081, width=59.1545, height=26.9417, cameraPosition=(-47.7323, 
    -12.4015, 17.0989), cameraUpVector=(-0.130073, 0.990752, 0.0386173), 
    cameraTarget=(8.94763, 17.8381, 1.94202), viewOffsetX=2.00111, 
    viewOffsetY=0.469232)
session.viewports['Viewport: 1'].view.setValues(nearPlane=47.8445, 
    farPlane=73.997, width=65.2933, height=29.7376, cameraPosition=(-52.3341, 
    6.10301, 23.9718), cameraUpVector=(0.154674, 0.978604, -0.135681), 
    cameraTarget=(8.96155, 15.7793, 1.4775), viewOffsetX=2.20877, 
    viewOffsetY=0.517926)
a = mdb.models['Model-1'].rootAssembly
v11 = a.instances['Part-1-1'].vertices
a.DatumPointByMidPoint(point1=v11[3], point2=v11[6])
session.viewports['Viewport: 1'].view.setValues(nearPlane=42.5909, 
    farPlane=82.1851, width=58.1237, height=26.4722, cameraPosition=(-26.2663, 
    55.4334, 40.1206), cameraUpVector=(0.447221, 0.479713, -0.754896), 
    cameraTarget=(4.94581, 11.7597, 1.71226), viewOffsetX=1.96623, 
    viewOffsetY=0.461054)
a = mdb.models['Model-1'].rootAssembly
v21 = a.instances['Part-1-1'].vertices
a.DatumPointByMidPoint(point1=v21[2], point2=v21[4])
session.viewports['Viewport: 1'].view.setValues(nearPlane=48.2011, 
    farPlane=75.9871, width=65.78, height=29.9592, cameraPosition=(-27.6282, 
    24.8732, 56.8172), cameraUpVector=(0.0350039, 0.833874, -0.550844), 
    cameraTarget=(5.2521, 12.9066, 0.848653), viewOffsetX=2.22523, 
    viewOffsetY=0.521786)
a = mdb.models['Model-1'].rootAssembly
d11 = a.datums
a.DatumPointByOffset(point=d11[5], vector=(0.0, 5.0, 0.0))
session.viewports['Viewport: 1'].view.setValues(nearPlane=46.0831, 
    farPlane=79.2221, width=62.8895, height=28.6428, cameraPosition=(-17.7133, 
    -5.86678, 58.8744), cameraUpVector=(-0.021636, 0.999667, -0.0140392), 
    cameraTarget=(4.31931, 15.8005, 0.548738), viewOffsetX=2.12745, 
    viewOffsetY=0.498858)
a = mdb.models['Model-1'].rootAssembly
d21 = a.datums
a.DatumPointByOffset(point=d21[4], vector=(0.0, -5.0, 0.0))
session.viewports['Viewport: 1'].view.setValues(nearPlane=47.905, 
    farPlane=77.0432, width=65.3759, height=29.7752, cameraPosition=(28.3572, 
    25.9088, 62.337), cameraUpVector=(-0.450286, 0.822549, -0.347355), 
    cameraTarget=(2.2318, 13.3168, 3.04365), viewOffsetX=2.21156, 
    viewOffsetY=0.518581)
session.viewports['Viewport: 1'].view.setValues(nearPlane=45.8541, 
    farPlane=78.827, width=62.577, height=28.5005, cameraPosition=(29.7276, 
    33.0565, 59.9878), cameraUpVector=(-0.414166, 0.784662, -0.461273), 
    cameraTarget=(2.10229, 13.2533, 3.4063), viewOffsetX=2.11688, 
    viewOffsetY=0.496379)
a = mdb.models['Model-1'].rootAssembly
d11 = a.datums
a.ReferencePoint(point=d11[7])
session.viewports['Viewport: 1'].view.setValues(nearPlane=42.983, 
    farPlane=81.698, width=111.757, height=50.8992, viewOffsetX=5.75834, 
    viewOffsetY=3.24396)
a = mdb.models['Model-1'].rootAssembly
d21 = a.datums
a.ReferencePoint(point=d21[6])
session.viewports['Viewport: 1'].view.setValues(nearPlane=44.4612, 
    farPlane=80.2198, width=75.8453, height=34.5434, viewOffsetX=7.92621, 
    viewOffsetY=7.39171)
session.viewports['Viewport: 1'].view.setValues(nearPlane=44.6797, 
    farPlane=90.2664, width=76.218, height=34.7132, cameraPosition=(30.9733, 
    61.9953, 48.1524), cameraUpVector=(-0.583121, 0.426606, -0.691359), 
    cameraTarget=(4.98404, 15.287, 9.42669), viewOffsetX=7.96516, 
    viewOffsetY=7.42803)
session.viewports['Viewport: 1'].view.setValues(nearPlane=45.7795, 
    farPlane=89.1667, width=56.9306, height=25.9288, viewOffsetX=4.8447, 
    viewOffsetY=6.55663)
session.viewports['Viewport: 1'].view.setValues(nearPlane=48.4881, 
    farPlane=78.2744, width=60.299, height=27.4629, cameraPosition=(20.5458, 
    29.5667, 65.4411), cameraUpVector=(-0.158162, 0.826823, -0.539767), 
    cameraTarget=(-0.381765, 12.8002, 5.12767), viewOffsetX=5.13134, 
    viewOffsetY=6.94455)
session.viewports['Viewport: 1'].view.setValues(nearPlane=45.1923, 
    farPlane=82.07, width=56.2004, height=25.5963, cameraPosition=(-39.1506, 
    41.6354, 44.2907), cameraUpVector=(0.445369, 0.697693, -0.561134), 
    cameraTarget=(0.43035, 12.4796, 0.244354), viewOffsetX=4.78256, 
    viewOffsetY=6.47253)
session.viewports['Viewport: 1'].view.setValues(nearPlane=45.4267, 
    farPlane=83.0875, width=56.492, height=25.7291, cameraPosition=(-48.636, 
    46.4996, 26.1593), cameraUpVector=(0.667193, 0.641854, -0.377991), 
    cameraTarget=(0.924313, 12.9018, -1.62117), viewOffsetX=4.80737, 
    viewOffsetY=6.50611)
session.viewports['Viewport: 1'].view.setValues(nearPlane=46.422, 
    farPlane=84.2087, width=57.7298, height=26.2928, cameraPosition=(-50.8075, 
    51.9739, 4.08984), cameraUpVector=(0.805507, 0.554529, -0.20894), 
    cameraTarget=(1.8574, 12.7135, -2.37738), viewOffsetX=4.9127, 
    viewOffsetY=6.64865)
session.viewports['Viewport: 1'].view.setValues(nearPlane=46.7601, 
    farPlane=84.7952, width=58.1502, height=26.4843, cameraPosition=(-48.7996, 
    54.9177, -3.959), cameraUpVector=(0.853039, 0.519259, -0.051915), 
    cameraTarget=(2.38167, 13.2381, -3.67081), viewOffsetX=4.94848, 
    viewOffsetY=6.69707)
session.viewports['Viewport: 1'].view.setValues(nearPlane=47.0292, 
    farPlane=79.4223, width=58.4849, height=26.6367, cameraPosition=(-52.6045, 
    32.7878, 27.3803), cameraUpVector=(0.553285, 0.791428, -0.259841), 
    cameraTarget=(2.58188, 12.2223, -2.42431), viewOffsetX=4.97696, 
    viewOffsetY=6.73561)
session.viewports['Viewport: 1'].view.setValues(nearPlane=45.6123, 
    farPlane=82.7907, width=56.7229, height=25.8342, cameraPosition=(-21.3864, 
    46.9005, 55.9167), cameraUpVector=(0.418713, 0.629717, -0.654321), 
    cameraTarget=(-2.26543, 13.4433, 2.32759), viewOffsetX=4.82702, 
    viewOffsetY=6.53268)
session.viewports['Viewport: 1'].view.setValues(nearPlane=41.5717, 
    farPlane=78.4474, width=51.6981, height=23.5457, cameraPosition=(-2.74123, 
    -23.406, 49.702), cameraUpVector=(0.0366341, 0.960177, 0.27698), 
    cameraTarget=(-0.549271, 14.9151, -3.99603), viewOffsetX=4.39942, 
    viewOffsetY=5.95398)
session.viewports['Viewport: 1'].view.setValues(nearPlane=47.6308, 
    farPlane=73.7725, width=59.2331, height=26.9775, cameraPosition=(4.91693, 
    -4.59332, 62.4911), cameraUpVector=(-0.145716, 0.983896, -0.103511), 
    cameraTarget=(0.236008, 10.3292, -1.63532), viewOffsetX=5.04063, 
    viewOffsetY=6.82177)
session.viewports['Viewport: 1'].view.setValues(nearPlane=48.6765, 
    farPlane=73.9916, width=60.5335, height=27.5698, cameraPosition=(6.81053, 
    19.2241, 66.9425), cameraUpVector=(-0.0697427, 0.879081, -0.471544), 
    cameraTarget=(-0.868368, 8.91537, 2.20029), viewOffsetX=5.15129, 
    viewOffsetY=6.97154)
a = mdb.models['Model-1'].rootAssembly
r1 = a.referencePoints
refPoints1=(r1[8], )
region1=a.Set(referencePoints=refPoints1, name='m_Set-1')
a = mdb.models['Model-1'].rootAssembly
s1 = a.instances['Part-1-1'].faces
side1Faces1 = s1.getSequenceFromMask(mask=('[#8 ]', ), )
region2=a.Surface(side1Faces=side1Faces1, name='s_Surf-1')
mdb.models['Model-1'].Coupling(name='Constraint-1', controlPoint=region1, 
    surface=region2, influenceRadius=WHOLE_SURFACE, couplingType=KINEMATIC, 
    alpha=0.0, localCsys=None, u1=OFF, u2=ON, u3=OFF, ur1=ON, ur2=ON, ur3=ON)
session.viewports['Viewport: 1'].view.setValues(nearPlane=46.9128, 
    farPlane=76.129, width=58.3403, height=26.5709, cameraPosition=(7.74266, 
    26.0607, 66.4548), cameraUpVector=(-0.144691, 0.814931, -0.561207), 
    cameraTarget=(-0.156442, 8.23082, 3.39542), viewOffsetX=4.96465, 
    viewOffsetY=6.71894)
session.viewports['Viewport: 1'].view.setValues(nearPlane=40.4167, 
    farPlane=85.0417, width=50.2619, height=22.8916, cameraPosition=(21.4474, 
    64.0137, 44.2086), cameraUpVector=(-0.629832, 0.230272, -0.741813), 
    cameraTarget=(4.73803, 9.06482, 11.6785), viewOffsetX=4.27719, 
    viewOffsetY=5.78856)
a = mdb.models['Model-1'].rootAssembly
r1 = a.referencePoints
refPoints1=(r1[9], )
region1=a.Set(referencePoints=refPoints1, name='m_Set-2')
a = mdb.models['Model-1'].rootAssembly
s1 = a.instances['Part-1-1'].faces
side1Faces1 = s1.getSequenceFromMask(mask=('[#2 ]', ), )
region2=a.Surface(side1Faces=side1Faces1, name='s_Surf-2')
mdb.models['Model-1'].Coupling(name='Constraint-2', controlPoint=region1, 
    surface=region2, influenceRadius=WHOLE_SURFACE, couplingType=KINEMATIC, 
    alpha=0.0, localCsys=None, u1=OFF, u2=ON, u3=OFF, ur1=ON, ur2=ON, ur3=ON)
session.viewports['Viewport: 1'].view.setValues(nearPlane=47.2362, 
    farPlane=78.1526, width=58.7426, height=26.7541, cameraPosition=(52.0648, 
    33.6415, 44.0899), cameraUpVector=(-0.133887, 0.578926, -0.804313), 
    cameraTarget=(-2.16285, 14.2766, 11.823), viewOffsetX=4.99888, 
    viewOffsetY=6.76526)
session.viewports['Viewport: 1'].view.setValues(nearPlane=44.3247, 
    farPlane=80.3924, width=55.1219, height=25.1051, cameraPosition=(33.7699, 
    40.8845, 55.7852), cameraUpVector=(0.0212744, 0.561224, -0.82739), 
    cameraTarget=(-3.59738, 12.8008, 9.18277), viewOffsetX=4.69077, 
    viewOffsetY=6.34828)
session.viewports['Viewport: 1'].view.setValues(nearPlane=46.5084, 
    farPlane=76.5799, width=57.8377, height=26.342, cameraPosition=(-12.0086, 
    30.0249, 63.5277), cameraUpVector=(0.262352, 0.775662, -0.574038), 
    cameraTarget=(-2.12519, 9.2599, 1.65751), viewOffsetX=4.92187, 
    viewOffsetY=6.66104)
session.viewports['Viewport: 1'].view.setValues(nearPlane=48.6581, 
    farPlane=73.925, width=60.5112, height=27.5596, cameraPosition=(-21.0463, 
    17.9399, 61.3796), cameraUpVector=(0.344665, 0.871011, -0.350066), 
    cameraTarget=(-1.4995, 10.3132, -1.2027), viewOffsetX=5.14937, 
    viewOffsetY=6.96893)
session.viewports['Viewport: 1'].view.setValues(nearPlane=50.5779, 
    farPlane=72.1559, width=62.8986, height=28.6469, cameraPosition=(8.10607, 
    10.5806, 66.7745), cameraUpVector=(-0.056994, 0.933827, -0.353156), 
    cameraTarget=(-1.68965, 8.86658, 1.52197), viewOffsetX=5.35253, 
    viewOffsetY=7.24388)
session.viewports['Viewport: 1'].assemblyDisplay.setValues(loads=ON, bcs=ON, 
    predefinedFields=ON, interactions=OFF, constraints=OFF, 
    engineeringFeatures=OFF)
a = mdb.models['Model-1'].rootAssembly
r1 = a.referencePoints
refPoints1=(r1[9], )
region = a.Set(referencePoints=refPoints1, name='Set-3')
mdb.models['Model-1'].ConcentratedForce(name='Load-1', createStepName='Step-1', 
    region=region, cf2=-1.0, distributionType=UNIFORM, field='', 
    localCsys=None)
a = mdb.models['Model-1'].rootAssembly
r1 = a.referencePoints
refPoints1=(r1[8], )
region = a.Set(referencePoints=refPoints1, name='Set-4')
mdb.models['Model-1'].DisplacementBC(name='BC-1', createStepName='Step-1', 
    region=region, u1=0.0, u2=0.0, u3=0.0, ur1=0.0, ur2=0.0, ur3=0.0, 
    amplitude=UNSET, fixed=OFF, distributionType=UNIFORM, fieldName='', 
    localCsys=None)
session.viewports['Viewport: 1'].assemblyDisplay.setValues(mesh=ON, loads=OFF, 
    bcs=OFF, predefinedFields=OFF, connectors=OFF)
session.viewports['Viewport: 1'].assemblyDisplay.meshOptions.setValues(
    meshTechnique=ON)
p = mdb.models['Model-1'].parts['Part-1']
session.viewports['Viewport: 1'].setValues(displayedObject=p)
session.viewports['Viewport: 1'].partDisplay.setValues(sectionAssignments=OFF, 
    engineeringFeatures=OFF, mesh=ON)
session.viewports['Viewport: 1'].partDisplay.meshOptions.setValues(
    meshTechnique=ON)
p = mdb.models['Model-1'].parts['Part-1']
p.seedPart(size=1.0, deviationFactor=0.1, minSizeFactor=0.1)
p = mdb.models['Model-1'].parts['Part-1']
p.generateMesh()
elemType1 = mesh.ElemType(elemCode=C3D20R, elemLibrary=STANDARD)
elemType2 = mesh.ElemType(elemCode=C3D15, elemLibrary=STANDARD)
elemType3 = mesh.ElemType(elemCode=C3D10, elemLibrary=STANDARD)
p = mdb.models['Model-1'].parts['Part-1']
c = p.cells
cells = c.getSequenceFromMask(mask=('[#1 ]', ), )
pickedRegions =(cells, )
p.setElementType(regions=pickedRegions, elemTypes=(elemType1, elemType2, 
    elemType3))
a1 = mdb.models['Model-1'].rootAssembly
a1.regenerate()
a = mdb.models['Model-1'].rootAssembly
session.viewports['Viewport: 1'].setValues(displayedObject=a)
session.viewports['Viewport: 1'].assemblyDisplay.setValues(mesh=OFF, 
    optimizationTasks=ON, geometricRestrictions=ON, stopConditions=ON)
session.viewports['Viewport: 1'].assemblyDisplay.meshOptions.setValues(
    meshTechnique=OFF)
session.viewports['Viewport: 1'].assemblyDisplay.setValues(
    optimizationTasks=OFF, geometricRestrictions=OFF, stopConditions=OFF)
mdb.Job(name='Job-1', model='Model-1', description='', type=ANALYSIS, 
    atTime=None, waitMinutes=0, waitHours=0, queue=None, memory=90, 
    memoryUnits=PERCENTAGE, getMemoryFromAnalysis=True, 
    explicitPrecision=SINGLE, nodalOutputPrecision=SINGLE, echoPrint=OFF, 
    modelPrint=OFF, contactPrint=OFF, historyPrint=OFF, userSubroutine='', 
    scratch='', resultsFormat=ODB, numThreadsPerMpiProcess=1, 
    multiprocessingMode=DEFAULT, numCpus=1, numGPUs=0)
mdb.jobs['Job-1'].writeInput(consistencyChecking=OFF)
#: The job input file has been written to "Job-1.inp".
mdb.jobs['Job-1'].submit(consistencyChecking=OFF)
#: The job input file "Job-1.inp" has been submitted for analysis.
#: Job Job-1: Analysis Input File Processor completed successfully.
#: Job Job-1: Abaqus/Standard completed successfully.
#: Job Job-1 completed successfully. 
o3 = session.openOdb(name='D:/COFO - HP/x - temp/abaqus/Job-1.odb')
#: Model: D:/COFO - HP/x - temp/abaqus/Job-1.odb
#: Number of Assemblies:         1
#: Number of Assembly instances: 0
#: Number of Part instances:     1
#: Number of Meshes:             2
#: Number of Element Sets:       2
#: Number of Node Sets:          8
#: Number of Steps:              1
session.viewports['Viewport: 1'].setValues(displayedObject=o3)
session.viewports['Viewport: 1'].makeCurrent()
session.viewports['Viewport: 1'].odbDisplay.display.setValues(plotState=(
    CONTOURS_ON_DEF, ))
session.viewports['Viewport: 1'].view.setValues(nearPlane=36.3601, 
    farPlane=63.0284, width=41.9128, height=19.089, cameraPosition=(-9.70632, 
    44.6986, 47.118), cameraUpVector=(-0.283152, 0.570274, -0.771111), 
    cameraTarget=(4.40347, 23.6482, 5.19196))
session.viewports['Viewport: 1'].odbDisplay.setPrimaryVariable(
    variableLabel='E', outputPosition=INTEGRATION_POINT, refinement=(INVARIANT, 
    'Max. Principal'), )
session.viewports['Viewport: 1'].odbDisplay.setPrimaryVariable(
    variableLabel='U', outputPosition=NODAL, refinement=(INVARIANT, 
    'Magnitude'), )
session.viewports['Viewport: 1'].view.setValues(nearPlane=38.2867, 
    farPlane=60.3247, width=44.1336, height=20.1005, cameraPosition=(24.6454, 
    27.4733, 49.8761), cameraUpVector=(-0.060927, 0.904877, -0.421291), 
    cameraTarget=(4.89042, 23.404, 5.23106))
session.viewports['Viewport: 1'].view.setValues(nearPlane=36.3345, 
    farPlane=61.8009, width=41.8833, height=19.0756, cameraPosition=(22.0483, 
    8.41842, 48.6294), cameraUpVector=(0.102435, 0.991744, -0.0771421), 
    cameraTarget=(4.87378, 23.2819, 5.22307))
session.viewports['Viewport: 1'].view.setValues(nearPlane=35.5299, 
    farPlane=63.2743, width=40.9559, height=18.6532, cameraPosition=(-31.0714, 
    44.5941, 30.9289), cameraUpVector=(0.807294, 0.590142, 0.00299008), 
    cameraTarget=(4.78942, 23.3393, 5.19496))
session.viewports['Viewport: 1'].view.setValues(nearPlane=38.3118, 
    farPlane=59.9562, width=44.1627, height=20.1137, cameraPosition=(-41.0463, 
    18.6971, 22.0656), cameraUpVector=(0.509084, 0.638169, 0.577558), 
    cameraTarget=(4.70617, 23.1232, 5.12099))
session.viewports['Viewport: 1'].view.setValues(nearPlane=35.7278, 
    farPlane=61.7953, width=41.1841, height=18.7571, cameraPosition=(3.85153, 
    -25.6943, 10.4326), cameraUpVector=(-0.258587, 0.435327, 0.862336), 
    cameraTarget=(4.83795, 22.9929, 5.08685))
session.viewports['Viewport: 1'].view.setValues(nearPlane=36.2879, 
    farPlane=61.4813, width=41.8298, height=19.0512, cameraPosition=(-1.78232, 
    1.56186, 48.5202), cameraUpVector=(0.109028, 0.98628, 0.123955), 
    cameraTarget=(4.86432, 22.8653, 4.90857))
session.viewports['Viewport: 1'].view.setValues(nearPlane=40.1128, 
    farPlane=57.7242, width=46.2388, height=21.0593, cameraPosition=(4.61623, 
    21.6879, 53.873), cameraUpVector=(0.0702164, 0.947765, -0.311144), 
    cameraTarget=(4.85056, 22.822, 4.89706))
session.viewports['Viewport: 1'].view.setValues(nearPlane=36.0587, 
    farPlane=61.8097, width=51.3156, height=23.3715, viewOffsetX=0.471676, 
    viewOffsetY=-0.115205)
session.viewports['Viewport: 1'].view.setValues(nearPlane=37.9149, 
    farPlane=60.1307, width=53.9571, height=24.5746, cameraPosition=(-13.9774, 
    21.7124, 50.2223), cameraUpVector=(0.227786, 0.942708, -0.243751), 
    cameraTarget=(4.82189, 22.7984, 4.99631), viewOffsetX=0.495956, 
    viewOffsetY=-0.121135)
session.viewports['Viewport: 1'].view.setValues(nearPlane=37.9721, 
    farPlane=60.3979, width=54.0387, height=24.6117, cameraPosition=(-2.63268, 
    17.2202, 53.2652), cameraUpVector=(0.0657496, 0.973816, -0.217621), 
    cameraTarget=(4.77001, 22.7377, 5.15343), viewOffsetX=0.496705, 
    viewOffsetY=-0.121318)
session.viewports['Viewport: 1'].view.setValues(nearPlane=37.0927, 
    farPlane=61.3072, width=52.7872, height=24.0417, cameraPosition=(-2.76134, 
    12.0286, 52.3787), cameraUpVector=(0.045645, 0.992426, -0.114054), 
    cameraTarget=(4.7662, 22.7108, 5.16419), viewOffsetX=0.485202, 
    viewOffsetY=-0.118508)
session.viewports['Viewport: 1'].view.setValues(nearPlane=37.1391, 
    farPlane=61.2608, width=47.5679, height=21.6646, viewOffsetX=-0.678829, 
    viewOffsetY=-0.531187)
a = mdb.models['Model-1'].rootAssembly
session.viewports['Viewport: 1'].setValues(displayedObject=a)
session.viewports['Viewport: 1'].assemblyDisplay.setValues(loads=ON, bcs=ON, 
    predefinedFields=ON, connectors=ON)
mdb.models['Model-1'].loads['Load-1'].setValues(cf2=-1000.0, 
    distributionType=UNIFORM, field='')
session.viewports['Viewport: 1'].assemblyDisplay.setValues(loads=OFF, bcs=OFF, 
    predefinedFields=OFF, connectors=OFF)
mdb.jobs['Job-1'].submit(consistencyChecking=OFF)
#: The job input file "Job-1.inp" has been submitted for analysis.
#: Job Job-1: Analysis Input File Processor completed successfully.
#: Job Job-1: Abaqus/Standard completed successfully.
#: Job Job-1 completed successfully. 
o3 = session.openOdb(name='D:/COFO - HP/x - temp/abaqus/Job-1.odb')
#: Model: D:/COFO - HP/x - temp/abaqus/Job-1.odb
#: Number of Assemblies:         1
#: Number of Assembly instances: 0
#: Number of Part instances:     1
#: Number of Meshes:             2
#: Number of Element Sets:       2
#: Number of Node Sets:          8
#: Number of Steps:              1
session.viewports['Viewport: 1'].setValues(displayedObject=o3)
session.viewports['Viewport: 1'].makeCurrent()
session.viewports['Viewport: 1'].odbDisplay.display.setValues(plotState=(
    CONTOURS_ON_DEF, ))
session.viewports['Viewport: 1'].odbDisplay.setPrimaryVariable(
    variableLabel='U', outputPosition=NODAL, refinement=(INVARIANT, 
    'Magnitude'), )
session.viewports['Viewport: 1'].view.setValues(nearPlane=36.2345, 
    farPlane=61.9842, width=41.768, height=19.0231, cameraPosition=(34.6517, 
    10.9354, 42.1635), cameraUpVector=(0.127332, 0.966403, -0.223275), 
    cameraTarget=(5.01898, 23.1798, 5.1232))
session.viewports['Viewport: 1'].view.setValues(nearPlane=34.1445, 
    farPlane=63.5166, width=39.3588, height=17.9258, cameraPosition=(33.072, 
    -14.9768, 17.7801), cameraUpVector=(0.469995, 0.851928, 0.230919), 
    cameraTarget=(5.01514, 23.1167, 5.06387))
a = mdb.models['Model-1'].rootAssembly
session.viewports['Viewport: 1'].setValues(displayedObject=a)
session.viewports['Viewport: 1'].assemblyDisplay.setValues(interactions=ON, 
    constraints=ON, connectors=ON, engineeringFeatures=ON)
session.viewports['Viewport: 1'].assemblyDisplay.setValues(loads=ON, bcs=ON, 
    predefinedFields=ON, interactions=OFF, constraints=OFF, 
    engineeringFeatures=OFF)
session.viewports['Viewport: 1'].view.setValues(nearPlane=46.596, 
    farPlane=76.8475, width=57.9467, height=26.3916, cameraPosition=(41.2749, 
    21.5169, 55.7262), cameraUpVector=(-0.326705, 0.857488, -0.397465), 
    cameraTarget=(-1.51097, 8.38605, 7.21091), viewOffsetX=4.93114, 
    viewOffsetY=6.67359)
session.viewports['Viewport: 1'].view.setValues(nearPlane=44.5651, 
    farPlane=79.0688, width=55.4211, height=25.2413, cameraPosition=(19.833, 
    34.9928, 63.0951), cameraUpVector=(-0.199913, 0.726016, -0.657978), 
    cameraTarget=(-1.52775, 8.26157, 6.651), viewOffsetX=4.71622, 
    viewOffsetY=6.38273)
session.viewports['Viewport: 1'].setValues(
    displayedObject=session.odbs['D:/COFO - HP/x - temp/abaqus/Job-1.odb'])
odb = session.odbs['D:/COFO - HP/x - temp/abaqus/Job-1.odb']
session.viewports['Viewport: 1'].setValues(displayedObject=odb)
session.viewports['Viewport: 1'].view.setValues(nearPlane=37.563, 
    farPlane=60.63, width=43.2994, height=19.7205, cameraPosition=(43.3106, 
    17.4302, 35.0036), cameraUpVector=(-0.285529, 0.958369, -0.00124712), 
    cameraTarget=(4.98173, 23.011, 5.00768))
session.viewports['Viewport: 1'].view.setValues(nearPlane=34.6957, 
    farPlane=63.0409, width=39.9942, height=18.2152, cameraPosition=(9.26507, 
    -16.3478, 33.948), cameraUpVector=(0.209473, 0.825277, 0.524441), 
    cameraTarget=(4.90776, 22.9376, 5.00539))
session.viewports['Viewport: 1'].view.setValues(nearPlane=35.8219, 
    farPlane=61.7451, width=41.2924, height=18.8065, cameraPosition=(1.2669, 
    -25.6666, 9.75428), cameraUpVector=(0.359077, 0.39052, 0.847678), 
    cameraTarget=(4.92764, 22.9608, 5.06553))
session.viewports['Viewport: 1'].view.setValues(nearPlane=34.8253, 
    farPlane=62.7622, width=40.1437, height=18.2833, cameraPosition=(42.4415, 
    -3.0329, -12.4168), cameraUpVector=(0.24772, 0.388797, 0.887396), 
    cameraTarget=(4.75346, 22.8651, 5.15932))
session.viewports['Viewport: 1'].view.setValues(nearPlane=35.2806, 
    farPlane=62.1041, width=40.6686, height=18.5224, cameraPosition=(-34.0291, 
    42.6426, -16.585), cameraUpVector=(0.657137, 0.71821, 0.228791), 
    cameraTarget=(5.06088, 22.6815, 5.17607))
session.viewports['Viewport: 1'].view.setValues(nearPlane=39.8934, 
    farPlane=57.5193, width=45.9859, height=20.9441, cameraPosition=(-43.8387, 
    21.0926, 4.8888), cameraUpVector=(0.300421, 0.950038, -0.084699), 
    cameraTarget=(5.12083, 22.8132, 5.04483))
session.viewports['Viewport: 1'].view.setValues(nearPlane=37.3799, 
    farPlane=60.1386, width=43.0885, height=19.6245, cameraPosition=(-30.4464, 
    21.0971, 38.5768), cameraUpVector=(0.139931, 0.947128, -0.288734), 
    cameraTarget=(5.04284, 22.8132, 4.84865))
session.viewports['Viewport: 1'].odbDisplay.basicOptions.setValues(
    bcDisplay=ON, connectorDisplay=ON, massElements=ON, springElements=ON, 
    spotWelds=ON, tracerParticles=ON, particleEdges=ON)
session.viewports['Viewport: 1'].view.setValues(nearPlane=37.1819, 
    farPlane=60.3365, width=52.9139, height=24.0994, viewOffsetX=0.245319, 
    viewOffsetY=-0.163326)
session.viewports['Viewport: 1'].view.setValues(nearPlane=34.111, 
    farPlane=63.4836, width=48.5437, height=22.109, cameraPosition=(-17.2576, 
    45.1919, 42.2394), cameraUpVector=(0.332398, 0.683542, -0.649833), 
    cameraTarget=(4.98378, 22.7011, 4.82945), viewOffsetX=0.225058, 
    viewOffsetY=-0.149837)
session.viewports['Viewport: 1'].odbDisplay.basicOptions.setValues(
    coordSystemDisplay=ON)
session.viewports['Viewport: 1'].view.setValues(nearPlane=30.9927, 
    farPlane=66.6018, width=85.0812, height=38.7499, viewOffsetX=9.13334, 
    viewOffsetY=-1.15519)
session.viewports['Viewport: 1'].view.setValues(nearPlane=41.3371, 
    farPlane=67.5402, width=113.479, height=51.6834, cameraPosition=(-5.26619, 
    20.8013, 58.537), cameraUpVector=(-0.198919, 0.896632, -0.395577), 
    cameraTarget=(2.96725, 19.5415, 10.2602), viewOffsetX=12.1818, 
    viewOffsetY=-1.54076)
session.viewports['Viewport: 1'].view.setValues(nearPlane=49.267, 
    farPlane=81.4099, width=135.248, height=61.5983, cameraPosition=(39.9732, 
    28.5147, 60.1252), cameraUpVector=(-0.0716856, 0.915621, -0.3956), 
    cameraTarget=(10.5495, 27.1328, 20.9799), viewOffsetX=14.5187, 
    viewOffsetY=-1.83633)
session.viewports['Viewport: 1'].view.setValues(nearPlane=38.8689, 
    farPlane=80.2529, width=106.703, height=48.5976, cameraPosition=(6.09186, 
    70.2212, 42.7349), cameraUpVector=(0.0974869, 0.446269, -0.889573), 
    cameraTarget=(-0.655006, 37.2755, 7.11086), viewOffsetX=11.4544, 
    viewOffsetY=-1.44876)
session.viewports['Viewport: 1'].view.setValues(nearPlane=38.4531, 
    farPlane=73.5568, width=105.562, height=48.0777, cameraPosition=(-7.62026, 
    51.4005, 52.6314), cameraUpVector=(0.102555, 0.731478, -0.674109), 
    cameraTarget=(-3.43245, 31.9009, 7.88503), viewOffsetX=11.3319, 
    viewOffsetY=-1.43326)
session.viewports['Viewport: 1'].view.setValues(nearPlane=40.8506, 
    farPlane=71.1593, width=73.5775, height=33.5106, viewOffsetX=15.1159, 
    viewOffsetY=-4.16618)
session.viewports['Viewport: 1'].odbDisplay.setPrimaryVariable(
    variableLabel='E', outputPosition=INTEGRATION_POINT, refinement=(INVARIANT, 
    'Max. Principal'), )
session.viewports['Viewport: 1'].view.setValues(nearPlane=43.8648, 
    farPlane=68.1451, width=37.7885, height=17.2106, viewOffsetX=10.3178, 
    viewOffsetY=-5.52324)
session.viewports['Viewport: 1'].view.setValues(nearPlane=44.3317, 
    farPlane=71.0422, width=38.1908, height=17.3938, cameraPosition=(4.72424, 
    -8.14867, 54.8556), cameraUpVector=(-0.144111, 0.937006, 0.318202), 
    cameraTarget=(-2.85882, 21.186, 16.359), viewOffsetX=10.4276, 
    viewOffsetY=-5.58203)
session.viewports['Viewport: 1'].view.setValues(nearPlane=47.1074, 
    farPlane=75.4653, width=40.582, height=18.4829, cameraPosition=(50.9344, 
    -19.2532, -5.10841), cameraUpVector=(0.390824, 0.502348, 0.7713), 
    cameraTarget=(16.8574, 10.2141, 14.1386), viewOffsetX=11.0805, 
    viewOffsetY=-5.93153)
session.viewports['Viewport: 1'].view.setValues(nearPlane=52.19, 
    farPlane=72.159, width=44.9606, height=20.4771, cameraPosition=(35.2422, 
    19.1067, -51.7626), cameraUpVector=(0.727904, 0.417638, 0.543815), 
    cameraTarget=(23.4205, 16.9685, -4.26851), viewOffsetX=12.276, 
    viewOffsetY=-6.57151)
session.viewports['Viewport: 1'].view.setValues(nearPlane=50.3545, 
    farPlane=69.6239, width=43.3793, height=19.7569, cameraPosition=(-53.2088, 
    29.978, -17.0349), cameraUpVector=(0.318108, 0.944678, -0.0799438), 
    cameraTarget=(-4.57312, 31.3704, -11.3209), viewOffsetX=11.8442, 
    viewOffsetY=-6.34039)
session.viewports['Viewport: 1'].view.setValues(nearPlane=47.7097, 
    farPlane=70.4102, width=41.1009, height=18.7192, cameraPosition=(-54.2303, 
    12.4239, -9.03353), cameraUpVector=(0.0218579, 0.991221, -0.130396), 
    cameraTarget=(-7.70885, 27.7511, -9.95724), viewOffsetX=11.2221, 
    viewOffsetY=-6.00737)
session.viewports['Viewport: 1'].view.setValues(nearPlane=50.0402, 
    farPlane=71.4599, width=43.1085, height=19.6336, cameraPosition=(-51.4228, 
    46.3078, -11.4418), cameraUpVector=(0.553449, 0.831374, -0.0501184), 
    cameraTarget=(-3.92007, 34.4128, -10.0213), viewOffsetX=11.7703, 
    viewOffsetY=-6.30081)
session.viewports['Viewport: 1'].view.setValues(nearPlane=49.215, 
    farPlane=72.285, width=47.1084, height=21.4554, viewOffsetX=13.706, 
    viewOffsetY=-9.88622)
session.viewports['Viewport: 1'].view.setValues(nearPlane=51.1459, 
    farPlane=76.5971, width=48.9567, height=22.2971, cameraPosition=(-45.4633, 
    5.9061, 45.725), cameraUpVector=(-0.43877, 0.73424, -0.518047), 
    cameraTarget=(-18.9809, 15.7306, 5.69775), viewOffsetX=14.2438, 
    viewOffsetY=-10.2741)
session.viewports['Viewport: 1'].view.setValues(nearPlane=51.7653, 
    farPlane=77.3307, width=49.5496, height=22.5672, cameraPosition=(-33.0113, 
    7.43246, 58.653), cameraUpVector=(-0.359183, 0.911597, -0.199947), 
    cameraTarget=(-18.4357, 21.2909, 13.9818), viewOffsetX=14.4163, 
    viewOffsetY=-10.3985)
session.viewports['Viewport: 1'].view.setValues(nearPlane=50.8551, 
    farPlane=78.6083, width=48.6784, height=22.1704, cameraPosition=(-31.6364, 
    -4.03827, 55.2232), cameraUpVector=(-0.426117, 0.903269, -0.0502901), 
    cameraTarget=(-18.2932, 18.0155, 13.5625), viewOffsetX=14.1628, 
    viewOffsetY=-10.2157)
session.viewports['Viewport: 1'].view.setValues(nearPlane=52.543, 
    farPlane=79.1699, width=50.2941, height=22.9063, cameraPosition=(5.09348, 
    8.6067, 72.4306), cameraUpVector=(0.207769, 0.976231, 0.0616804), 
    cameraTarget=(-3.29685, 29.8579, 29.0945), viewOffsetX=14.6329, 
    viewOffsetY=-10.5548)
session.viewports['Viewport: 1'].view.setValues(nearPlane=51.0328, 
    farPlane=79.8826, width=48.8487, height=22.2479, cameraPosition=(-15.9736, 
    -11.4126, 60.5209), cameraUpVector=(0.108306, 0.903529, 0.414614), 
    cameraTarget=(-11.31, 22.2806, 25.264), viewOffsetX=14.2123, 
    viewOffsetY=-10.2514)
session.viewports['Viewport: 1'].view.setValues(nearPlane=52.9197, 
    farPlane=79.8234, width=50.6548, height=23.0705, cameraPosition=(17.5346, 
    8.40485, 71.6021), cameraUpVector=(-0.241025, 0.966222, 0.0912286), 
    cameraTarget=(-3.42054, 23.9918, 30.1538), viewOffsetX=14.7378, 
    viewOffsetY=-10.6304)
session.viewports['Viewport: 1'].view.setValues(nearPlane=52.0458, 
    farPlane=82.6717, width=49.8183, height=22.6896, cameraPosition=(14.6656, 
    -38.485, 38.136), cameraUpVector=(-0.0233654, 0.607539, 0.793946), 
    cameraTarget=(-2.60626, 5.33521, 24.6639), viewOffsetX=14.4944, 
    viewOffsetY=-10.4549)
session.viewports['Viewport: 1'].view.setValues(nearPlane=51.4192, 
    farPlane=82.1731, width=49.2186, height=22.4164, cameraPosition=(18.3905, 
    -23.6464, 55.6392), cameraUpVector=(0.449343, 0.789107, 0.418809), 
    cameraTarget=(5.17999, 17.1463, 31.9439), viewOffsetX=14.3199, 
    viewOffsetY=-10.329)
session.viewports['Viewport: 1'].view.setValues(nearPlane=52.3486, 
    farPlane=79.8522, width=50.1082, height=22.8216, cameraPosition=(8.27002, 
    6.09402, 72.1468), cameraUpVector=(0.175885, 0.98, 0.0930813), 
    cameraTarget=(-2.74708, 28.7265, 30.1179), viewOffsetX=14.5787, 
    viewOffsetY=-10.5157)
session.viewports['Viewport: 1'].view.setValues(nearPlane=53.4152, 
    farPlane=79.6192, width=51.1292, height=23.2866, cameraPosition=(19.1581, 
    15.8092, 72.7345), cameraUpVector=(-0.155976, 0.987638, -0.0156017), 
    cameraTarget=(-2.15604, 28.3092, 30.4321), viewOffsetX=14.8758, 
    viewOffsetY=-10.73)
session.viewports['Viewport: 1'].view.setValues(nearPlane=53.6092, 
    farPlane=79.0318, width=51.3149, height=23.3712, cameraPosition=(14.4186, 
    19.1894, 73.643), cameraUpVector=(-0.133305, 0.988147, -0.0761311), 
    cameraTarget=(-3.77362, 29.8542, 29.4237), viewOffsetX=14.9298, 
    viewOffsetY=-10.769)
session.viewports['Viewport: 1'].view.setValues(nearPlane=53.8074, 
    farPlane=80.118, width=51.5047, height=23.4576, cameraPosition=(33.7585, 
    21.2992, 68.8201), cameraUpVector=(-0.104948, 0.990769, -0.0858092), 
    cameraTarget=(4.24597, 31.3831, 31.0395), viewOffsetX=14.985, 
    viewOffsetY=-10.8088)
session.viewports['Viewport: 1'].view.setValues(nearPlane=53.5188, 
    farPlane=80.3415, width=51.2285, height=23.3318, cameraPosition=(32.654, 
    18.9113, 69.1769), cameraUpVector=(-0.0785431, 0.995025, -0.061294), 
    cameraTarget=(4.02178, 30.7247, 31.2205), viewOffsetX=14.9046, 
    viewOffsetY=-10.7508)
session.viewports['Viewport: 1'].view.setValues(nearPlane=53.5161, 
    farPlane=82.4144, width=51.226, height=23.3307, cameraPosition=(22.3005, 
    -44.0616, 21.766), cameraUpVector=(0.22829, 0.437862, 0.869575), 
    cameraTarget=(3.25644, 1.0633, 22.8229), viewOffsetX=14.9039, 
    viewOffsetY=-10.7503)
odb = session.odbs['D:/COFO - HP/x - temp/abaqus/Job-1.odb']
xyList = xyPlot.xyDataListFromField(odb=odb, outputPosition=NODAL, variable=((
    'U', NODAL), ), nodePick=(('PART-1-1', 341, (
    '[#200400 #400801 #801002 #1002004 #2004008 #4008010 #8010020', 
    ' #10020040 #20040080 #40080100 #80100200 #200400 #400801 #801002', 
    ' #1002004 #2004008 #4008010 #8010020 #10020040 #20040080 #40080100', 
    ' #80100200 #200400 #400801 #801002 #1002004 #2004008 #4008010', 
    ' #8010020 #10020040 #20040080 #40080100 #80100200 #200400 #400801', 
    ' #801002 #1002004 #2004008 #4008010 #8010020 #10020040 #40080', 
    ' #0:2 #69 #b000000 #0 #16000 #0 #2c', 
    ' #5800000 #0 #b000 #0 #16 #2c00000 #0', 
    ' #5800 #0 #b #1a00000 #1800000:9 #0 #3400', 
    ' #3000:9 #80000000 #6:10 #d00000 #c00000:9 #0 #1a00', 
    ' #1800:9 #40000000 #3:10 #680000 #600000:9 #0 #d00', 
    ' #c00:9 #a0000000 #80000001:9 #1 ]', )), ), )
xyp = session.XYPlot('XYPlot-1')
chartName = xyp.charts.keys()[0]
chart = xyp.charts[chartName]
curveList = session.curveSet(xyData=xyList)
chart.setValues(curvesToPlot=curveList)
session.charts[chartName].autoColor(lines=True, symbols=True)
session.viewports['Viewport: 1'].setValues(displayedObject=xyp)
#: Warning: Requested operation will result in the creation of a very large number of xyDataObjects. Performance can be affected. Please reduce the number of specified entities using Display Group operations before re-performing this operation.
odb = session.odbs['D:/COFO - HP/x - temp/abaqus/Job-1.odb']
xyList = xyPlot.xyDataListFromField(odb=odb, outputPosition=NODAL, variable=((
    'U', NODAL, ((INVARIANT, 'Magnitude'), )), ), nodePick=(('PART-1-1', 341, (
    '[#200400 #400801 #801002 #1002004 #2004008 #4008010 #8010020', 
    ' #10020040 #20040080 #40080100 #80100200 #200400 #400801 #801002', 
    ' #1002004 #2004008 #4008010 #8010020 #10020040 #20040080 #40080100', 
    ' #80100200 #200400 #400801 #801002 #1002004 #2004008 #4008010', 
    ' #8010020 #10020040 #20040080 #40080100 #80100200 #200400 #400801', 
    ' #801002 #1002004 #2004008 #4008010 #8010020 #10020040 #40080', 
    ' #0:2 #69 #b000000 #0 #16000 #0 #2c', 
    ' #5800000 #0 #b000 #0 #16 #2c00000 #0', 
    ' #5800 #0 #b #1a00000 #1800000:9 #0 #3400', 
    ' #3000:9 #80000000 #6:10 #d00000 #c00000:9 #0 #1a00', 
    ' #1800:9 #40000000 #3:10 #680000 #600000:9 #0 #d00', 
    ' #c00:9 #a0000000 #80000001:9 #1 ]', )), ), )
xyp = session.xyPlots['XYPlot-1']
chartName = xyp.charts.keys()[0]
chart = xyp.charts[chartName]
curveList = session.curveSet(xyData=xyList)
chart.setValues(curvesToPlot=curveList)
session.charts[chartName].autoColor(lines=True, symbols=True)
odb = session.odbs['D:/COFO - HP/x - temp/abaqus/Job-1.odb']
xyList = xyPlot.xyDataListFromField(odb=odb, outputPosition=NODAL, variable=((
    'U', NODAL, ((COMPONENT, 'U1'), )), ), nodePick=(('PART-1-1', 341, (
    '[#200400 #400801 #801002 #1002004 #2004008 #4008010 #8010020', 
    ' #10020040 #20040080 #40080100 #80100200 #200400 #400801 #801002', 
    ' #1002004 #2004008 #4008010 #8010020 #10020040 #20040080 #40080100', 
    ' #80100200 #200400 #400801 #801002 #1002004 #2004008 #4008010', 
    ' #8010020 #10020040 #20040080 #40080100 #80100200 #200400 #400801', 
    ' #801002 #1002004 #2004008 #4008010 #8010020 #10020040 #40080', 
    ' #0:2 #69 #b000000 #0 #16000 #0 #2c', 
    ' #5800000 #0 #b000 #0 #16 #2c00000 #0', 
    ' #5800 #0 #b #1a00000 #1800000:9 #0 #3400', 
    ' #3000:9 #80000000 #6:10 #d00000 #c00000:9 #0 #1a00', 
    ' #1800:9 #40000000 #3:10 #680000 #600000:9 #0 #d00', 
    ' #c00:9 #a0000000 #80000001:9 #1 ]', )), ), )
xyp = session.xyPlots['XYPlot-1']
chartName = xyp.charts.keys()[0]
chart = xyp.charts[chartName]
curveList = session.curveSet(xyData=xyList)
chart.setValues(curvesToPlot=curveList)
session.charts[chartName].autoColor(lines=True, symbols=True)
odb = session.odbs['D:/COFO - HP/x - temp/abaqus/Job-1.odb']
xyList = xyPlot.xyDataListFromField(odb=odb, outputPosition=NODAL, variable=((
    'U', NODAL, ((COMPONENT, 'U2'), )), ), nodePick=(('PART-1-1', 341, (
    '[#200400 #400801 #801002 #1002004 #2004008 #4008010 #8010020', 
    ' #10020040 #20040080 #40080100 #80100200 #200400 #400801 #801002', 
    ' #1002004 #2004008 #4008010 #8010020 #10020040 #20040080 #40080100', 
    ' #80100200 #200400 #400801 #801002 #1002004 #2004008 #4008010', 
    ' #8010020 #10020040 #20040080 #40080100 #80100200 #200400 #400801', 
    ' #801002 #1002004 #2004008 #4008010 #8010020 #10020040 #40080', 
    ' #0:2 #69 #b000000 #0 #16000 #0 #2c', 
    ' #5800000 #0 #b000 #0 #16 #2c00000 #0', 
    ' #5800 #0 #b #1a00000 #1800000:9 #0 #3400', 
    ' #3000:9 #80000000 #6:10 #d00000 #c00000:9 #0 #1a00', 
    ' #1800:9 #40000000 #3:10 #680000 #600000:9 #0 #d00', 
    ' #c00:9 #a0000000 #80000001:9 #1 ]', )), ), )
xyp = session.xyPlots['XYPlot-1']
chartName = xyp.charts.keys()[0]
chart = xyp.charts[chartName]
curveList = session.curveSet(xyData=xyList)
chart.setValues(curvesToPlot=curveList)
session.charts[chartName].autoColor(lines=True, symbols=True)
odb = session.odbs['D:/COFO - HP/x - temp/abaqus/Job-1.odb']
xyList = xyPlot.xyDataListFromField(odb=odb, outputPosition=NODAL, variable=((
    'U', NODAL, ((COMPONENT, 'U3'), )), ), nodePick=(('PART-1-1', 341, (
    '[#200400 #400801 #801002 #1002004 #2004008 #4008010 #8010020', 
    ' #10020040 #20040080 #40080100 #80100200 #200400 #400801 #801002', 
    ' #1002004 #2004008 #4008010 #8010020 #10020040 #20040080 #40080100', 
    ' #80100200 #200400 #400801 #801002 #1002004 #2004008 #4008010', 
    ' #8010020 #10020040 #20040080 #40080100 #80100200 #200400 #400801', 
    ' #801002 #1002004 #2004008 #4008010 #8010020 #10020040 #40080', 
    ' #0:2 #69 #b000000 #0 #16000 #0 #2c', 
    ' #5800000 #0 #b000 #0 #16 #2c00000 #0', 
    ' #5800 #0 #b #1a00000 #1800000:9 #0 #3400', 
    ' #3000:9 #80000000 #6:10 #d00000 #c00000:9 #0 #1a00', 
    ' #1800:9 #40000000 #3:10 #680000 #600000:9 #0 #d00', 
    ' #c00:9 #a0000000 #80000001:9 #1 ]', )), ), )
xyp = session.xyPlots['XYPlot-1']
chartName = xyp.charts.keys()[0]
chart = xyp.charts[chartName]
curveList = session.curveSet(xyData=xyList)
chart.setValues(curvesToPlot=curveList)
session.charts[chartName].autoColor(lines=True, symbols=True)
odb = session.odbs['D:/COFO - HP/x - temp/abaqus/Job-1.odb']
session.viewports['Viewport: 1'].setValues(displayedObject=odb)
session.viewports['Viewport: 1'].odbDisplay.display.setValues(plotState=(
    SYMBOLS_ON_DEF, ))
session.viewports['Viewport: 1'].odbDisplay.setSymbolVariable(
    variableLabel='U', outputPosition=NODAL, vectorQuantity=RESULTANT, )
session.viewports['Viewport: 1'].view.setValues(nearPlane=54.5068, 
    farPlane=84.1497, width=52.1744, height=23.7626, cameraPosition=(30.356, 
    -34.2222, -32.4409), cameraUpVector=(0.777287, 0.107762, 0.619849), 
    cameraTarget=(17.9136, -4.30737, 4.30611), viewOffsetX=15.1798, 
    viewOffsetY=-10.9493)
session.viewports['Viewport: 1'].view.setValues(nearPlane=56.4669, 
    farPlane=84.6722, width=54.0506, height=24.6171, cameraPosition=(-3.90323, 
    40.9633, -66.9491), cameraUpVector=(0.976682, 0.208606, 0.0507602), 
    cameraTarget=(14.8468, 21.5134, -26.0812), viewOffsetX=15.7257, 
    viewOffsetY=-11.343)
session.viewports['Viewport: 1'].view.setValues(nearPlane=58.8604, 
    farPlane=82.3831, width=56.3417, height=25.6606, cameraPosition=(14.8189, 
    21.4593, -68.9816), cameraUpVector=(0.966948, 0.067856, 0.24578), 
    cameraTarget=(20.2709, 11.6764, -21.2887), viewOffsetX=16.3923, 
    viewOffsetY=-11.8238)
session.viewports['Viewport: 1'].view.setValues(nearPlane=57.9343, 
    farPlane=84.5731, width=55.4552, height=25.2569, cameraPosition=(25.0293, 
    37.417, -65.9565), cameraUpVector=(0.92311, -0.126129, 0.363262), 
    cameraTarget=(22.4692, 16.2689, -21.8403), viewOffsetX=16.1344, 
    viewOffsetY=-11.6378)
session.viewports['Viewport: 1'].view.setValues(nearPlane=59.4579, 
    farPlane=82.1219, width=56.9137, height=25.9211, cameraPosition=(25.6201, 
    14.2596, -66.2992), cameraUpVector=(0.909555, -0.102685, 0.402697), 
    cameraTarget=(21.3909, 7.11286, -18.018), viewOffsetX=16.5587, 
    viewOffsetY=-11.9439)
session.viewports['Viewport: 1'].odbDisplay.commonOptions.setValues(
    renderStyle=WIREFRAME, )
session.viewports['Viewport: 1'].view.setValues(nearPlane=60.1243, 
    farPlane=81.4554, width=42.4796, height=19.3472, viewOffsetX=18.3187, 
    viewOffsetY=-13.9337)
session.viewports['Viewport: 1'].view.setValues(nearPlane=60.2557, 
    farPlane=82.3244, width=42.5724, height=19.3894, cameraPosition=(17.2603, 
    23.8342, -69.2072), cameraUpVector=(0.954722, -0.10105, 0.279813), 
    cameraTarget=(19.1581, 10.9016, -21.993), viewOffsetX=18.3587, 
    viewOffsetY=-13.9641)
session.viewports['Viewport: 1'].view.setValues(nearPlane=59.3022, 
    farPlane=83.7313, width=41.8987, height=19.0826, cameraPosition=(-13.895, 
    22.0721, -68.138), cameraUpVector=(0.988741, 0.0686567, -0.132956), 
    cameraTarget=(8.98228, 12.0946, -25.9822), viewOffsetX=18.0682, 
    viewOffsetY=-13.7431)
session.viewports['Viewport: 1'].view.setValues(nearPlane=59.8767, 
    farPlane=80.6748, width=42.3046, height=19.2675, cameraPosition=(3.89207, 
    0.271734, -65.8762), cameraUpVector=(0.993269, 0.0826821, 0.0811186), 
    cameraTarget=(16.1702, 3.87906, -18.587), viewOffsetX=18.2432, 
    viewOffsetY=-13.8762)
session.viewports['Viewport: 1'].view.setValues(nearPlane=53.7122, 
    farPlane=82.5371, width=37.9493, height=17.2839, cameraPosition=(10.9364, 
    -42.4197, -26.1879), cameraUpVector=(0.974567, 0.223481, -0.0165859), 
    cameraTarget=(19.5906, -4.84646, 4.03444), viewOffsetX=16.365, 
    viewOffsetY=-12.4476)
session.viewports['Viewport: 1'].view.setValues(nearPlane=58.0832, 
    farPlane=80.7046, width=41.0376, height=18.6904, cameraPosition=(4.2587, 
    20.5672, -68.9059), cameraUpVector=(0.994221, 0.0189369, 0.105671), 
    cameraTarget=(15.9784, 9.47261, -22.6501), viewOffsetX=17.6968, 
    viewOffsetY=-13.4606)
session.viewports['Viewport: 1'].view.setValues(nearPlane=57.8745, 
    farPlane=80.9134, width=40.8901, height=18.6233, cameraPosition=(2.39565, 
    19.0401, -68.8001), cameraUpVector=(0.994245, -0.064282, 0.0857047), 
    cameraTarget=(14.1153, 7.9455, -22.5443), viewOffsetX=17.6332, 
    viewOffsetY=-13.4122)
session.viewports['Viewport: 1'].view.setValues(nearPlane=57.9995, 
    farPlane=80.7518, width=40.9785, height=18.6635, cameraPosition=(9.99311, 
    21.7149, -68.7291), cameraUpVector=(0.976596, -0.109149, 0.185326), 
    cameraTarget=(16.3689, 8.52837, -21.9797), viewOffsetX=17.6713, 
    viewOffsetY=-13.4412)
session.viewports['Viewport: 1'].view.setValues(nearPlane=57.9818, 
    farPlane=80.766, width=40.966, height=18.6578, cameraPosition=(5.84711, 
    19.3825, -68.8303), cameraUpVector=(0.98588, -0.100945, 0.133606), 
    cameraTarget=(14.8843, 7.69915, -22.1198), viewOffsetX=17.6659, 
    viewOffsetY=-13.4371)
session.viewports['Viewport: 1'].view.setValues(nearPlane=57.9823, 
    farPlane=80.7655, width=40.9664, height=18.658, cameraPosition=(6.82687, 
    20.0938, -68.842), cameraUpVector=(0.987854, -0.0592004, 0.143665), 
    cameraTarget=(15.8641, 8.4104, -22.1315), viewOffsetX=17.6661, 
    viewOffsetY=-13.4372)
leaf = dgo.LeafFromOdbElementPick(elementPick=(('PART-1-1', 900, (
    '[#dff7fdff #f7fdff7f #fdff7fdf #ff7fdff7 #7fdff7fd #dff7fdff #f7fdff7f', 
    ' #fdff7fdf #ff7fdff7 #7fdff7fd #dff7fdff #f7fdff7f #fdff7fdf #ff7fdff7', 
    ' #7fdff7fd #dff7fdff #f7fdff7f #fdff7fdf #ff7fdff7 #7fdff7fd #dff7fdff', 
    ' #f7fdff7f #fdff7fdf #ff7fdff7 #7fdff7fd #dff7fdff #f7fdff7f #fdff7fdf', 
    ' #ff7fdff7 #7fdff7fd #dff7fdff #7f ]', )), ), )
session.viewports['Viewport: 1'].odbDisplay.displayGroup.remove(leaf=leaf)
session.viewports['Viewport: 1'].view.setValues(session.views['Back'])
session.viewports['Viewport: 1'].view.setValues(session.views['Top'])
session.viewports['Viewport: 1'].view.setProjection(projection=PARALLEL)
session.viewports['Viewport: 1'].view.setValues(nearPlane=37.6606, 
    farPlane=56.2975, width=3.69985, height=1.68508, cameraPosition=(5.44745, 
    69.729, 5.33613), cameraTarget=(5.44745, 22.75, 5.33613))
session.viewports['Viewport: 1'].view.setValues(nearPlane=37.194, 
    farPlane=56.6564, cameraPosition=(1.36995, 69.5516, 5.19945), 
    cameraUpVector=(-0.0199047, -0.00465399, -0.999791))
a = mdb.models['Model-1'].rootAssembly
session.viewports['Viewport: 1'].setValues(displayedObject=a)
session.viewports['Viewport: 1'].assemblyDisplay.setValues(loads=OFF, bcs=OFF, 
    predefinedFields=OFF, connectors=OFF)
session.viewports['Viewport: 1'].view.setValues(session.views['Front'])
session.viewports['Viewport: 1'].view.setValues(session.views['Back'])
session.viewports['Viewport: 1'].view.setValues(session.views['Top'])
#: 
#: Point 1: 0., 28.75, 0.  Point 2: 5., 33.75, 5.
#:    Distance: 8.660254  Components: 5., 5., 5.
#: 
#: Point 1: 10., 28.75, 0.  Point 2: 5., 33.75, 5.
#:    Distance: 8.660254  Components: -5., 5., 5.
#: 
#: Point 1: 10., 28.75, 10.  Point 2: 5., 33.75, 5.
#:    Distance: 8.660254  Components: -5., 5., -5.
#: 
#: Point 1: 0., 28.75, 10.  Point 2: 5., 33.75, 5.
#:    Distance: 8.660254  Components: 5., 5., -5.
session.viewports['Viewport: 1'].view.setValues(nearPlane=53.7033, 
    farPlane=92.6695, width=37.2344, height=16.9583, viewOffsetX=3.37998, 
    viewOffsetY=-2.55956)
odb = session.odbs['D:/COFO - HP/x - temp/abaqus/Job-1.odb']
session.viewports['Viewport: 1'].setValues(displayedObject=odb)
session.viewports['Viewport: 1'].view.setValues(nearPlane=36.9952, 
    farPlane=56.8553, width=6.96193, height=3.17078, cameraPosition=(0.95627, 
    69.5154, 5.12891), cameraTarget=(5.03377, 22.7138, 5.26559))
session.viewports['Viewport: 1'].view.setValues(session.views['Top'])
session.viewports['Viewport: 1'].view.setValues(nearPlane=37.6565, 
    farPlane=56.3016, width=4.62678, height=2.10725, cameraPosition=(5.15781, 
    69.729, 5.10621), cameraTarget=(5.15781, 22.75, 5.10621))
session.viewports['Viewport: 1'].view.setValues(nearPlane=36.6978, 
    farPlane=57.2571, cameraPosition=(2.27952, 69.25, 11.1471), 
    cameraUpVector=(0.0209767, 0.130077, -0.991282))
session.viewports['Viewport: 1'].view.setValues(nearPlane=36.0283, 
    farPlane=57.9266, width=14.7439, height=6.71505, cameraPosition=(2.34958, 
    69.2875, 10.892), cameraTarget=(5.22787, 22.7875, 4.85114))
session.viewports['Viewport: 1'].view.setValues(nearPlane=35.4069, 
    farPlane=58.3513, cameraPosition=(-11.1798, 66.807, 4.55702), 
    cameraUpVector=(0.181869, 0.0612286, -0.981415), cameraTarget=(5.22832, 
    22.7876, 4.85135))
session.viewports['Viewport: 1'].view.setValues(nearPlane=34.6148, 
    farPlane=59.1434, width=27.7432, height=12.6355, cameraPosition=(-11.3523, 
    66.7355, 3.47117), cameraTarget=(5.05586, 22.7161, 3.7655))
session.viewports['Viewport: 1'].view.setValues(session.views['Back'])
session.viewports['Viewport: 1'].view.setValues(session.views['Top'])
session.viewports['Viewport: 1'].odbDisplay.display.setValues(plotState=(
    UNDEFORMED, ))
session.viewports['Viewport: 1'].odbDisplay.display.setValues(plotState=(
    CONTOURS_ON_DEF, ))
session.viewports['Viewport: 1'].odbDisplay.display.setValues(plotState=(
    SYMBOLS_ON_DEF, ))
session.viewports['Viewport: 1'].odbDisplay.display.setValues(plotState=(
    UNDEFORMED, ))
session.viewports['Viewport: 1'].odbDisplay.display.setValues(plotState=(
    SYMBOLS_ON_DEF, ))
a = mdb.models['Model-1'].rootAssembly
session.viewports['Viewport: 1'].setValues(displayedObject=a)
session.viewports['Viewport: 1'].assemblyDisplay.setValues(loads=ON, bcs=ON, 
    predefinedFields=ON, connectors=ON)
session.viewports['Viewport: 1'].view.setValues(nearPlane=53.3795, 
    farPlane=94.8635, width=37.0099, height=16.856, cameraPosition=(-2.00968, 
    84.6273, 34.2627), cameraUpVector=(0.177691, 0.420431, -0.889755), 
    cameraTarget=(5.71929, 18.2423, 4.43761), viewOffsetX=3.3596, 
    viewOffsetY=-2.54413)
session.viewports['Viewport: 1'].view.setValues(nearPlane=51.9334, 
    farPlane=94.1978, width=36.0072, height=16.3994, cameraPosition=(-10.4795, 
    86.053, 22.7429), cameraUpVector=(0.168773, 0.295009, -0.940471), 
    cameraTarget=(5.66306, 17.1653, 4.03085), viewOffsetX=3.26858, 
    viewOffsetY=-2.47521)
session.viewports['Viewport: 1'].view.setValues(nearPlane=51.3725, 
    farPlane=94.7586, width=48.8593, height=22.2528, viewOffsetX=2.81577, 
    viewOffsetY=-2.19721)
a = mdb.models['Model-1'].rootAssembly
r1 = a.referencePoints
refPoints1=(r1[9], )
region = a.Set(referencePoints=refPoints1, name='Set-5')
mdb.models['Model-1'].DisplacementBC(name='BC-2', createStepName='Step-1', 
    region=region, u1=UNSET, u2=UNSET, u3=UNSET, ur1=0.0, ur2=0.0, ur3=0.0, 
    amplitude=UNSET, fixed=OFF, distributionType=UNIFORM, fieldName='', 
    localCsys=None)
session.viewports['Viewport: 1'].assemblyDisplay.setValues(loads=OFF, bcs=OFF, 
    predefinedFields=OFF, connectors=OFF)
mdb.jobs['Job-1'].submit(consistencyChecking=OFF)
#: The job input file "Job-1.inp" has been submitted for analysis.
#: Job Job-1: Analysis Input File Processor completed successfully.
#: Job Job-1: Abaqus/Standard completed successfully.
#: Job Job-1 completed successfully. 
o3 = session.openOdb(name='D:/COFO - HP/x - temp/abaqus/Job-1.odb')
#: Model: D:/COFO - HP/x - temp/abaqus/Job-1.odb
#: Number of Assemblies:         1
#: Number of Assembly instances: 0
#: Number of Part instances:     1
#: Number of Meshes:             2
#: Number of Element Sets:       2
#: Number of Node Sets:          9
#: Number of Steps:              1
session.viewports['Viewport: 1'].setValues(displayedObject=o3)
session.viewports['Viewport: 1'].makeCurrent()
session.viewports['Viewport: 1'].view.setValues(nearPlane=34.1817, 
    farPlane=63.7978, cameraPosition=(31.5733, 43.5307, 41.0913), 
    cameraUpVector=(-0.409113, 0.727942, -0.550206), cameraTarget=(5, 23.75, 
    5))
session.viewports['Viewport: 1'].odbDisplay.display.setValues(plotState=(
    SYMBOLS_ON_DEF, ))
session.viewports['Viewport: 1'].view.setValues(nearPlane=33.9409, 
    farPlane=66.0284, cameraPosition=(24.055, 64.8021, 23.9737), 
    cameraUpVector=(-0.653512, 0.242615, -0.71698), cameraTarget=(4.9215, 
    23.9721, 4.82126))
session.viewports['Viewport: 1'].odbDisplay.setSymbolVariable(
    variableLabel='U', outputPosition=NODAL, vectorQuantity=RESULTANT, )
session.viewports['Viewport: 1'].view.setValues(nearPlane=35.2313, 
    farPlane=64.592, cameraPosition=(5.10779, 60.0934, 38.0894), 
    cameraUpVector=(-0.695533, 0.190849, -0.692683), cameraTarget=(4.54438, 
    23.8784, 5.10221))
session.viewports['Viewport: 1'].view.setValues(nearPlane=39.1531, 
    farPlane=59.6675, cameraPosition=(3.56413, 20.6832, 54.3204), 
    cameraUpVector=(-0.790585, 0.520261, -0.322961), cameraTarget=(4.51587, 
    23.1505, 5.40201))
session.viewports['Viewport: 1'].view.setValues(nearPlane=38.4372, 
    farPlane=60.563, cameraPosition=(-2.0263, 27.0787, 53.8002), 
    cameraUpVector=(-0.754018, 0.453823, -0.474871), cameraTarget=(4.46829, 
    23.2049, 5.39758))
session.viewports['Viewport: 1'].view.setValues(cameraPosition=(-2.0263, 
    27.0787, 53.8002), cameraUpVector=(-0.864014, 0.185277, -0.468137))
session.viewports['Viewport: 1'].view.setValues(session.views['Front'])
leaf = dgo.LeafFromOdbElementPick(elementPick=(('PART-1-1', 900, (
    '[#dff7fdff #f7fdff7f #fdff7fdf #ff7fdff7 #7fdff7fd #dff7fdff #f7fdff7f', 
    ' #fdff7fdf #ff7fdff7 #7fdff7fd #dff7fdff #f7fdff7f #fdff7fdf #ff7fdff7', 
    ' #7fdff7fd #dff7fdff #f7fdff7f #fdff7fdf #ff7fdff7 #7fdff7fd #dff7fdff', 
    ' #f7fdff7f #fdff7fdf #ff7fdff7 #7fdff7fd #dff7fdff #f7fdff7f #fdff7fdf', 
    ' #ff7fdff7 #7fdff7fd #dff7fdff #7f ]', )), ), )
session.viewports['Viewport: 1'].odbDisplay.displayGroup.remove(leaf=leaf)
session.viewports['Viewport: 1'].view.setValues(session.views['Bottom'])
session.viewports['Viewport: 1'].view.setValues(nearPlane=35.619, 
    farPlane=58.3228, width=33.7337, height=15.3639, cameraPosition=(5.91426, 
    -24.2209, 3.55237), cameraTarget=(5.91426, 22.75, 3.55237))
session.viewports['Viewport: 1'].odbDisplay.display.setValues(plotState=(
    CONTOURS_ON_DEF, ))
session.viewports['Viewport: 1'].view.setValues(nearPlane=35.0673, 
    farPlane=58.8745, width=41.6465, height=18.9678, cameraPosition=(7.8711, 
    -24.2209, 3.23723), cameraTarget=(7.8711, 22.75, 3.23723))
session.viewports['Viewport: 1'].view.setValues(nearPlane=35.5006, 
    farPlane=62.3189, cameraPosition=(15.8729, -2.77075, -35.3753), 
    cameraUpVector=(-0.195438, -0.836304, 0.51225), cameraTarget=(7.8711, 
    22.75, 3.23723))
session.viewports['Viewport: 1'].view.setValues(nearPlane=37.7367, 
    farPlane=61.7453, cameraPosition=(24.7121, 12.5883, -39.5709), 
    cameraUpVector=(-0.00201747, -0.969733, 0.244157), cameraTarget=(8.2215, 
    23.3589, 3.07091))
session.viewports['Viewport: 1'].odbDisplay.display.setValues(plotState=(
    UNDEFORMED, ))
session.viewports['Viewport: 1'].odbDisplay.display.setValues(plotState=(
    SYMBOLS_ON_DEF, ))
leaf = dgo.Leaf(leafType=DEFAULT_MODEL)
session.viewports['Viewport: 1'].odbDisplay.displayGroup.replace(leaf=leaf)
session.viewports['Viewport: 1'].view.setValues(nearPlane=37.3783, 
    farPlane=62.1038, width=51.4155, height=23.417, cameraPosition=(25.3953, 
    12.9078, -39.3874), cameraTarget=(8.90469, 23.6784, 3.25442))
session.viewports['Viewport: 1'].view.setValues(nearPlane=39.3015, 
    farPlane=58.4393, cameraPosition=(7.3717, 23.2418, -43.9571), 
    cameraUpVector=(-0.055067, -0.998237, 0.0221345), cameraTarget=(7.90094, 
    24.2539, 2.99993))
session.viewports['Viewport: 1'].view.setValues(session.views['Top'])
session.viewports['Viewport: 1'].view.setValues(session.views['Bottom'])
session.viewports['Viewport: 1'].view.setValues(session.views['Back'])
session.viewports['Viewport: 1'].view.setValues(nearPlane=36.1933, 
    farPlane=57.7484, width=78.0855, height=35.5637, cameraPosition=(4.35924, 
    18.7683, -42.004), cameraTarget=(4.35924, 18.7683, 4.96691))
session.viewports['Viewport: 1'].odbDisplay.commonOptions.setValues(
    deformationScaling=UNIFORM)
session.viewports['Viewport: 1'].view.setValues(nearPlane=8917.75, 
    farPlane=11744, width=15413.9, height=7020.21, cameraPosition=(-2830.44, 
    -1580.23, -10359), cameraTarget=(-2830.44, -1580.23, 4.96691))
session.viewports['Viewport: 1'].odbDisplay.commonOptions.setValues(
    uniformScaleFactor=4E+20)
session.viewports['Viewport: 1'].view.setValues(nearPlane=4.90519e+18, 
    farPlane=5.10193e+18, width=9.32649e+17, height=4.24771e+17, 
    cameraPosition=(-1.7092e+17, -1.58953e+17, -5.00687e+18), cameraTarget=(
    -1.7092e+17, -1.58953e+17, 4.96691))
session.viewports['Viewport: 1'].view.setValues(session.views['Right'])
#* VisError: Deformation and/or analytical surface extent is too large as 
#* compared with the model.
session.viewports['Viewport: 1'].view.setValues(session.views['Left'])
#* VisError: Deformation and/or analytical surface extent is too large as 
#* compared with the model.
session.viewports['Viewport: 1'].odbDisplay.commonOptions.setValues(
    deformationScaling=AUTO)
session.viewports['Viewport: 1'].view.setValues(session.views['Right'])
session.viewports['Viewport: 1'].view.setValues(session.views['Back'])
session.viewports['Viewport: 1'].view.setValues(session.views['Right'])
session.viewports['Viewport: 1'].view.setValues(session.views['Back'])
session.viewports['Viewport: 1'].view.setValues(session.views['Front'])
session.viewports['Viewport: 1'].view.setValues(session.views['Back'])
session.viewports['Viewport: 1'].view.setValues(session.views['Front'])
session.viewports['Viewport: 1'].view.setValues(session.views['Back'])
session.viewports['Viewport: 1'].view.setValues(session.views['Front'])
session.viewports['Viewport: 1'].view.setValues(session.views['Back'])
session.viewports['Viewport: 1'].odbDisplay.setSymbolVariable(
    variableLabel='RF', outputPosition=NODAL, vectorQuantity=RESULTANT, )
session.viewports['Viewport: 1'].view.setValues(nearPlane=37.6687, 
    farPlane=56.2731, width=56.9243, height=25.926, cameraPosition=(4.2464, 
    16.7676, -42.004), cameraTarget=(4.2464, 16.7676, 4.96691))
session.viewports['Viewport: 1'].odbDisplay.setSymbolVariable(
    variableLabel='UR', outputPosition=NODAL, vectorQuantity=RESULTANT, )
session.viewports['Viewport: 1'].view.setValues(nearPlane=36.1253, 
    farPlane=57.8165, width=64.0398, height=29.1667, cameraPosition=(3.98704, 
    16.0906, -42.004), cameraTarget=(3.98704, 16.0906, 4.96691))
session.viewports['Viewport: 1'].odbDisplay.setSymbolVariable(
    variableLabel='U', outputPosition=NODAL, vectorQuantity=RESULTANT, )
session.viewports['Viewport: 1'].odbDisplay.setSymbolVariable(
    variableLabel='U', outputPosition=NODAL, refinement=(COMPONENT, 'U2'), 
    vectorQuantity=VECTOR_COMPONENT, )
session.viewports['Viewport: 1'].odbDisplay.setSymbolVariable(
    variableLabel='U', outputPosition=NODAL, refinement=(COMPONENT, 'U3'), 
    vectorQuantity=VECTOR_COMPONENT, )
session.viewports['Viewport: 1'].view.setValues(nearPlane=33.236, 
    farPlane=60.7057, width=120.502, height=54.8823, cameraPosition=(3.81302, 
    10.2094, -42.004), cameraTarget=(3.81302, 10.2094, 4.96691))
session.viewports['Viewport: 1'].odbDisplay.setSymbolVariable(
    variableLabel='U', outputPosition=NODAL, refinement=(COMPONENT, 'U1'), 
    vectorQuantity=VECTOR_COMPONENT, )
session.viewports['Viewport: 1'].view.setValues(nearPlane=38.3825, 
    farPlane=55.5592, width=46.6851, height=21.2625, cameraPosition=(3.05584, 
    16.9647, -42.004), cameraTarget=(3.05584, 16.9647, 4.96691))
session.viewports['Viewport: 1'].view.setValues(session.views['Top'])
session.viewports['Viewport: 1'].odbDisplay.setSymbolVariable(
    variableLabel='U', outputPosition=NODAL, refinement=(COMPONENT, 'U3'), 
    vectorQuantity=VECTOR_COMPONENT, )
session.viewports['Viewport: 1'].view.setValues(nearPlane=35.3577, 
    farPlane=58.5841, width=37.4818, height=17.071, cameraPosition=(8.40872, 
    69.7209, 5.40721), cameraTarget=(8.40872, 22.75, 5.40721))
a = mdb.models['Model-1'].rootAssembly
session.viewports['Viewport: 1'].setValues(displayedObject=a)
session.viewports['Viewport: 1'].assemblyDisplay.setValues(
    adaptiveMeshConstraints=ON)
mdb.models['Model-1'].steps['Step-1'].setValues(maxNumInc=10000, 
    initialInc=0.01, maxInc=0.05, nlgeom=ON)
session.viewports['Viewport: 1'].assemblyDisplay.setValues(
    adaptiveMeshConstraints=OFF)
mdb.jobs['Job-1'].submit(consistencyChecking=OFF)
#: The job input file "Job-1.inp" has been submitted for analysis.
#: Job Job-1: Analysis Input File Processor completed successfully.
#: Job Job-1: Abaqus/Standard completed successfully.
#: Job Job-1 completed successfully. 
session.viewports['Viewport: 1'].setValues(displayedObject=None)
