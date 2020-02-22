import time
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import fnmatch
import logging
import tarfile
import os
import glob

WORKING_DIR = '/data/cbioportal/cbio-env/dropoff'
LOADER_SCRIPT = '/data/cbioportal/cbio-env/importer/scripts/importer/metaImport.py'
PORTAL_HOME = '/data/cbioportal/cbio-env/importer'

logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO,
                    filename=os.path.join(WORKING_DIR, "cbio-%s.log"%time.strftime("%Y%m%d-%H%M%S")),
                    filemode='w')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-1s: %(levelname)-1s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

def untar_file(tar_ball):
    """
    untar archieved study and start importing data
    """
    study_name, genome = None, None
    my_tar = tarfile.open(tar_ball, "r:gz")
    for filename in my_tar.getnames():
        try:
            if filename.split("/")[-1] == 'meta_study.txt':
                f = my_tar.extractfile(filename)
                data = f.read().decode("utf-8")
                for line in data.split("\n"):
                    parts = line.split(":")
                    if parts[0] == 'cancer_study_identifier':
                        study_name = parts[1].strip().lower()
                    elif parts[0] == 'reference_genome':
                        genome = parts[1].strip()
                logging.info(f"study identifier: {study_name}")
                logging.info(f"reference genome: {genome}")
                outdir = os.path.join(WORKING_DIR, study_name)
                if not os._exists(outdir):
                    os.mkdir(outdir)
                untar_cmd = "tar zxvf %s -C %s" %(tar_ball,outdir)
                logging.info(untar_cmd)
                if (os.system(untar_cmd) == 0):
                    study_dir = next(os.walk(outdir))[1]
                    loader_cmd = "export PORTAL_HOME=%s;%s -s %s -jar %s -ucsc %s -ncbi %s -n -o"%(
                        PORTAL_HOME, LOADER_SCRIPT, os.path.join(outdir, study_dir[0]),
                        os.path.join(PORTAL_HOME,"scripts.jar"), genome,
                        "GRCh37" if genome == 'hg19' else "GRCh38")
                    logging.info(f"kick off loader {loader_cmd}")
                    if (os.system(loader_cmd) == 0):
                        logging.info(f"{study_name} imported")
                        try:
                            os.remove(tar_ball)
                            os.system("rm -rf %s"%outdir)
                            if not glob.glob(os.path.join(WORKING_DIR,'*.tar.gz')):
                                restart_cmd = '/usr/local/tomcat/bin/catalina.sh stop;sleep 8;/usr/local/tomcat/bin/catalina.sh start'
                                if (os.system(restart_cmd) == 0):
                                    logging.info("cBioPortal database restarted")
                        except:
                            logging.error(f"{tar_ball}/{outdir} does not exist")
                    else:
                       logging.info(f"importing {study_name} failed, please check log file for errors")
                       try:
                           os.remove(tar_ball)
                           os.system("rm -rf %s"%outdir)
                       except:
                           logging.error(f"{tar_ball}/{outdir} can not be removed, please check your folder permissions.")
                else:
                    logging.info(f"{tar_ball}/{outdir} does not exist")
        except:
            logging.warning ('Did not find %s in tar archive' % filename)
    my_tar.close()

def fire_loader(file):
    if fnmatch.fnmatch(file, '*.tar.gz'):
        logging.info(f"Unzip file {file} ...")
        untar_file(file)
    elif fnmatch.fnmatch(file, '*.zip'):
        logging.info("Got zip file: %s" % file)

def on_created(event):
    logging.info(f"{event.src_path} was added!")
    fire_loader(event.src_path)

def on_deleted(event):
    logging.info(f"{event.src_path} was deleted!")

def on_modified(event):
    logging.info(f"{event.src_path} was modified")

def on_moved(event):
    logging.info(f"{event.src_path} was moved to {event.dest_path}")

def setup_handler():
    my_event_handler = PatternMatchingEventHandler(patterns="*", ignore_patterns="",
                                                   ignore_directories=False, case_sensitive=True)
    my_event_handler.on_created = on_created
    my_event_handler.on_deleted = on_deleted
    return my_event_handler

if __name__ == "__main__":
    my_event_handler = setup_handler()
    my_observer = Observer()
    my_observer.schedule(my_event_handler, WORKING_DIR, recursive=True)
    my_observer.start()
    try:
        while True:
            time.sleep(120)
    except KeyboardInterrupt:
        my_observer.stop()
        my_observer.join()