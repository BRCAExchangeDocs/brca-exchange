import subprocess
import os
import urllib2
import tarfile
import datetime
import luigi

from shutil import copyfile

# Import methods from pipeline files
import sys
sys.path.insert(0, '../esp')
import espExtract

sys.path.insert(0, '../data_merging')
import convert_tsv_to_vcf

sys.path.insert(0, '../clinvar')
import clinVarBrca
import clinVarParse

#######################
# Convenience methods #
#######################

def create_path_if_nonexistent(path):
  if not os.path.exists(path):
    os.makedirs(path)
  return path

def print_subprocess_output_and_error(sp):
  out, err = sp.communicate()
  if out:
      print "standard output of subprocess:"
      print out
  if err:
      print "standard error of subprocess:"
      print err

def download_file_and_display_progress(url, file_name=None):
  if file_name is None:
    file_name = url.split('/')[-1]

  u = urllib2.urlopen(url)
  f = open(file_name, 'wb')
  meta = u.info()
  file_size = int(meta.getheaders("Content-Length")[0])
  print "Downloading: %s Bytes: %s" % (file_name, file_size)

  file_size_dl = 0
  block_sz = 8192
  while True:
      buffer = u.read(block_sz)
      if not buffer:
          break

      file_size_dl += len(buffer)
      f.write(buffer)
      status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
      status = status + chr(8)*(len(status)+1)
      print status,

  f.close()
  print "Finished downloading %s" % (file_name)

def download_file_with_basic_auth(url, file_name, username, password):
  p = urllib2.HTTPPasswordMgrWithDefaultRealm()

  p.add_password(None, url, username, password)

  handler = urllib2.HTTPBasicAuthHandler(p)
  opener = urllib2.build_opener(handler)
  urllib2.install_opener(opener)

  data = urllib2.urlopen(brca2_data_url).read()
  f = open(file_name, "wb")
  f.write(data)
  f.close()
  print "Finished downloading %s" % (file_name)


###############################
# Globals / Env / Directories #
###############################

brca_resources_dir = os.environ['BRCA_RESOURCES'] = create_path_if_nonexistent(os.path.abspath('../brca/brca-resources'))
pipeline_input_dir = os.environ['PIPELINE_INPUT'] = create_path_if_nonexistent(os.path.abspath('../brca/pipeline-data/data/pipeline_input'))
brca_pipeline_data_dir = os.environ['BRCA_PIPELINE_DATA'] = create_path_if_nonexistent(os.path.abspath('../brca/pipeline-data'))

bic_file_dir = os.environ['BIC'] = create_path_if_nonexistent(os.path.abspath('../brca/pipeline-data/data/BIC'))
clinvar_file_dir = os.environ['CLINVAR'] = create_path_if_nonexistent(os.path.abspath('../brca/pipeline-data/data/ClinVar'))
esp_file_dir = os.environ['ESP'] = create_path_if_nonexistent(os.path.abspath('../brca/pipeline-data/data/ESP'))
lovd_file_dir = os.environ['LOVD'] = create_path_if_nonexistent(os.path.abspath('../brca/pipeline-data/data/LOVD'))
ex_lovd_file_dir = os.environ['EXLOVD'] = create_path_if_nonexistent(os.path.abspath('../brca/pipeline-data/data/exLOVD'))
exac_file_dir = os.environ['EXAC'] = create_path_if_nonexistent(os.path.abspath('../brca/pipeline-data/data/exac'))
g1k_file_dir = os.environ['G1K'] = create_path_if_nonexistent(os.path.abspath('../brca/pipeline-data/data/G1K'))

luigi_dir = os.environ['LUIGI'] = os.getcwd()

bic_method_dir = os.environ['BIC_METHODS'] = os.path.abspath('../bic')
clinvar_method_dir = os.environ['CLINVAR_METHODS'] = os.path.abspath('../clinvar')
esp_method_dir = os.environ['ESP_METHODS'] = os.path.abspath('../esp')
lovd_method_dir = os.environ['LOVD_METHODS'] = os.path.abspath('../lovd')
g1k_method_dir = os.environ['G1K_METHODS'] = os.path.abspath('../1000_Genomes')
data_merging_method_dir = os.environ['DATA_MERGING_METHODS'] = os.path.abspath('../data_merging')


######################
####### Tasks ########
######################


class ConvertLatestClinvarToVCF(luigi.Task):
    date = luigi.DateParameter(default=datetime.date.today())

    def output(self):
      return luigi.LocalTarget(pipeline_input_dir + "/ClinVarBrca.vcf")

    def run(self):
      os.chdir(clinvar_file_dir)

      # Download latest gzipped ClinVarFullRelease
      download_file_and_display_progress("ftp://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/ClinVarFullRelease_00-latest.xml.gz")
      
      # Convert downloaded data to xml
      os.chdir(clinvar_method_dir)
      clinvar_xml_file = clinvar_file_dir + "/ClinVarBrca.xml"
      writable_clinvar_xml_file = open(clinvar_xml_file, "w")
      args = ["python", "clinVarBrca.py", clinvar_file_dir + "/ClinVarFullRelease_00-latest.xml.gz"]
      print "Running clinVarBrca.py with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=writable_clinvar_xml_file, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)
      print "Completed writing %s." % (writable_clinvar_xml_file)

      # Convert xml to txt
      clinvar_txt_file = clinvar_file_dir + "/ClinVarBrca.txt"
      writable_clinvar_txt_file = open(clinvar_txt_file, "w")
      args = ["python", "clinVarParse.py", clinvar_file_dir + "/ClinVarBrca.xml", "--assembly", "GRCh38"]
      print "Running clinVarParse.py with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=writable_clinvar_txt_file, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)
      print "Completed writing %s." % (writable_clinvar_txt_file)

      # Convert txt to vcf
      os.chdir(data_merging_method_dir)
      args = ["python", "convert_tsv_to_vcf.py", "-i", clinvar_file_dir + "/ClinVarBrca.txt", "-o", pipeline_input_dir + "/ClinVarBrca.vcf", "-s", "ClinVar"]
      print "Running convert_tsv_to_vcf.py with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)
      print "Completed writing %s." % (pipeline_input_dir + "/ClinVarBrca.vcf")

      # NOTE: If we prefer to use the Clinvar Makefile instead of python, it can be run with the commented out code below.

      # # Create required xml file for make to run properly
      # clinvar_xml_file = clinvar_file_dir + "/ClinVarBrca.xml"
      # if not os.path.exists(clinvar_xml_file):
      #   open(clinvar_xml_file, 'w').close() 

      # # Makefile requires a particular environment variable for output
      # my_env = os.environ.copy()
      # my_env["BRCA_PIPELINE_DATA"] = brca_pipeline_data_dir
      
      # # Convert gzipped file to vcf using makefile in pipeline/clinvar/
      # print "Converting %s to VCF format. This takes a while..." % (file_name)
      # sp = subprocess.Popen(["make"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd="../clinvar", env=my_env)
      # print_subprocess_output_and_error(sp)

class DownloadAndExtractFilesFromESPTar(luigi.Task):
    date = luigi.DateParameter(default=datetime.date.today())

    def output(self):
      return luigi.LocalTarget(pipeline_input_dir + "/esp.brca12.sorted.hg38.vcf")

    # NOTE: This task requires some setup to run properly.
    # 1. vcf module must be installed (`pip install PyVCF`)
    # 2. VCFtools must be installed: https://vcftools.github.io/index.html 
    # VCFtools installation is tricky and will require some extra work
    def run(self):
      os.chdir(esp_file_dir)

      # Download ESP data
      esp_data_url = "http://evs.gs.washington.edu/evs_bulk_data/ESP6500SI-V2-SSA137.GRCh38-liftover.snps_indels.vcf.tar.gz"
      download_file_and_display_progress(esp_data_url)

      # Extract contents of tarfile
      tar = tarfile.open(file_name, "r:gz")
      tar.extractall()
      tar.close()
      print "Finished extracting files from %s" % (file_name)

      os.chdir(esp_method_dir)

      # Extract data for BRCA1 region
      brca1_region_file = esp_file_dir + "/ESP6500SI-V2-SSA137.GRCh38-liftover.chr17.snps_indels.vcf"
      brca1_region_output = esp_file_dir + "/esp.brca1.vcf"
      args = ["python", "espExtract.py", brca1_region_file, "--start", "43044295", "--end", "43125483", "--full", "1", "-o", brca1_region_output]
      print "Calling espExtract.py for BRCA1 region with the following arguments: %s" % (args)
      sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)

      # Extract data for BRCA2 region
      brca2_region_file = esp_file_dir + '/ESP6500SI-V2-SSA137.GRCh38-liftover.chr13.snps_indels.vcf'
      brca2_region_output = esp_file_dir + "/esp.brca2.vcf"
      args = ["python", "espExtract.py", brca2_region_file, "--start", "43044295", "--end", "43125483", "--full", "1", "-o", brca2_region_output]
      print "Calling espExtract.py for BRCA 2 region with the following arguments: %s" % (args)
      sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)

      # Concatenate extracted BRCA1/BRCA2 region data
      # Note: requires correct installation of VCF tools and export PERL5LIB=/path/to/your/vcftools-directory/src/perl/ in path
      concatenated_brca_output_file = esp_file_dir + "/esp.brca12.hg38.vcf"
      writable_concatenated_brca_output_file = open(concatenated_brca_output_file, 'w')
      args = ["vcf-concat", brca1_region_output, brca2_region_output]
      print "Calling vcf-concat with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=writable_concatenated_brca_output_file, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)

      writable_concatenated_brca_output_file.close()
      print "Concatenation complete."

      # Sort concatenated BRCA1/2 data
      print "Sorting concatenated data into pipeline_input directory."
      with self.output().open("w") as vcf_file:
        args = ["vcf-sort", concatenated_brca_output_file]
        print "Calling vcf-sort with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=vcf_file, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

      print "Sorting of concatenated files complete."

class DownloadAndExtractFilesFromBIC(luigi.Task):

    # NOTE: U/P can be found in /hive/groups/cgl/brca/phase1/data/bic/account.txt at UCSC
    date = luigi.DateParameter(default=datetime.date.today())
    u = luigi.Parameter()
    p = luigi.Parameter()

    def output(self):
        return luigi.LocalTarget(pipeline_input_dir + "/bicSnp.sorted.hg38.vcf")

    def run(self):
      os.chdir(bic_file_dir)

      # Download brca1 data
      brca1_data_url = "https://research.nhgri.nih.gov/projects/bic/Member/cgi-bin/bic_query_result.cgi/brca1_data.txt?table=brca1_exons&download=1&submit=Download"
      brca1_file_name = "brca1_data.txt"
      download_file_with_basic_auth(brca1_data_url, brca1_file_name, self.u, self.p)

      # Download brca2 data
      brca2_data_url = "https://research.nhgri.nih.gov/projects/bic/Member/cgi-bin/bic_query_result.cgi/brca2_data.txt?table=brca2_exons&download=1&submit=Download"
      brca2_file_name = "brca2_data.txt"
      download_file_with_basic_auth(brca2_data_url, brca2_file_name, self.u, self.p)

      # Convert files to vcf
      os.chdir(bic_method_dir)

      bic_vcf_file = bic_file_dir + "/bicSnp.hg19.vcf"
      writable_bic_vcf_file = open(bic_vcf_file, 'w')
      args = ["python", "convBic.py", "--brca1", bic_file_dir + "/" + brca1_file_name, "--brca2", bic_file_dir + "/" + brca2_file_name]
      print "Converting BRCA1/2 BIC data to vcf with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=writable_bic_vcf_file, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)

      writable_bic_vcf_file.close()
      print "Conversion of BIC data to VCF complete."

      # Note: CrossMap.py must be installed `pip install CrossMap` for the next step
      os.chdir(luigi_dir)
      bic_hg38_vcf_file = bic_file_dir + "/bicSnp.hg38.vcf"
      writable_bic_hg38_vcf_file = open(bic_hg38_vcf_file, 'w')
      args = ["CrossMap.py", "vcf", brca_resources_dir + "/hg19ToHg38.over.chain.gz", bic_vcf_file, brca_resources_dir + "/hg38.fa", bic_hg38_vcf_file]
      print "Running crossmap.py with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=writable_bic_hg38_vcf_file, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)
      print "Crossmap.py execution complete, created bicSnp.hg38.vcf."

      # Sort hg38 vcf file, requires VCFtools.
      with self.output().open("w") as vcf_file:
        args = ["vcf-sort", bic_hg38_vcf_file]
        print "Running vcf-sort with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=vcf_file, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)
      print "Sorting of hg38 vcf file complete."

class ExtractAndConvertFilesFromEXLOVD(luigi.Task):
    date = luigi.DateParameter(default=datetime.date.today())

    def output(self):
      return luigi.LocalTarget(pipeline_input_dir + "/exLOVD_brca12.sorted.hg38.vcf")
    
    def run(self):
      os.chdir(lovd_method_dir)
      
      # extract_data.py -u http://hci-exlovd.hci.utah.edu/ -l BRCA1 BRCA2 -o $EXLOVD
      ex_lovd_data_host_url = "http://hci-exlovd.hci.utah.edu/"
      args = ["extract_data.py", "-u", ex_lovd_data_host_url, "-l", "BRCA1", "BRCA2", "-o", ex_lovd_file_dir]
      print "Running extract_data.py with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)
      print "Extracted data from %s." % (ex_lovd_data_host_url)

      # Convert extracted flat file to vcf format ./lovd2vcf -i $EXLOVD/BRCA1.txt -o $EXLOVD/exLOVD_brca1.hg19.vcf -a exLOVDAnnotation -b 1 -r $BRCA_RESOURCES/refseq_annotation.hg19.gp -g $BRCA_RESOURCES/hg19.fa
      args = ["./lovd2vcf", "-i", ex_lovd_file_dir + "/BRCA1.txt", "-o", ex_lovd_file_dir + "/exLOVD_brca1.hg19.vcf", "-a", "exLOVDAnnotation", "-b", "1", "-r", brca_resources_dir + "/refseq_annotation.hg19.gp", "-g", brca_resources_dir + "/hg19.fa"]
      print "Running lovd2vcf with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)
      print "Converted extracted BRCA1 flat file to vcf format."

      # ./lovd2vcf -i output_directory/BRCA2.txt -o exLOVD_brca2.vcf -a $EXLOVD/exLOVDAnnotation -b 2 -r $BRCA_RESOURCES/refseq_annotation.hg19.gp -g $BRCA_RESOURCES/hg19.fa
      args = ["./lovd2vcf", "-i", ex_lovd_file_dir + "/BRCA2.txt", "-o", "exLOVD_brca2.vcf", "-a", ex_lovd_file_dir + "exLOVDAnnotation", "-b", "2", "-r", brca_resources_dir + "/refseq_annotation.hg19.gp", "-g", brca_resources_dir + "/hg19.fa"]
      print "Running lovd2vcf with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)
      print "Converted extracted BRCA2 flat file to vcf format."

      # vcf-concat $EXLOVD/exLOVD_brca1.hg19.vcf $EXLOVD/exLOVD_brca2.hg19.vcf > $EXLOVD/exLOVD_brca12.hg19.vcf
      ex_lovd_brca12_hg19_vcf_file = ex_lovd_file_dir + "/exLOVD_brca12.hg19.vcf"
      writable_ex_lovd_brca12_hg19_vcf_file = open(ex_lovd_brca12_hg19_vcf_file, 'w')
      args = ["vcf-concat", ex_lovd_file_dir + "/exLOVD_brca1.hg19.vcf", ex_lovd_file_dir + "/exLOVD_brca2.hg19.vcf"]
      print "Running lovd2vcf with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=writable_ex_lovd_brca12_hg19_vcf_file, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)
      print "Concatenated BRCA1 and BRCA2 vcf files into %s." % (ex_lovd_brca12_hg19_vcf_file)
      
      # `CrossMap.py vcf $BRCA_RESOURCES/hg19ToHg38.over.chain.gz $EXLOVD/exLOVD_brca12.hg19.vcf $BRCA_RESOURCES/hg38.fa $EXLOVD/exLOVD_brca12.hg38.vcf
      args = ["CrossMap.py", "vcf", brca_resources_dir + "/hg19ToHg38.over.chain.gz", ex_lovd_brca12_hg19_vcf_file, brca_resources_dir + "/hg38.fa", ex_lovd_file_dir + "/exLOVD_brca12.hg38.vcf"]
      print "Running CrossMap.py with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)
      print "Crossmap complete."
      
      # vcf-sort $EXLOVD/exLOVD_brca12.hg38.vcf > $EXLOVD/exLOVD_brca12.sorted.hg38.vcf
      print "Sorting concatenated file into pipeline_input directory."
      with self.output().open("w") as vcf_file:
        args = ["vcf-sort", ex_lovd_file_dir + "/exLOVD_brca12.hg38.vcf"]
        print "Running lovd2vcf with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=vcf_file, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)
        print "Sorted BRCA1/2 hg38 vcf file into %s" % (vcf_file)

class ExtractAndConvertFilesFromLOVD(luigi.Task):
    date = luigi.DateParameter(default=datetime.date.today())
    
    def output(self):
      return luigi.LocalTarget(pipeline_input_dir + "/sharedLOVD_brca12.sorted.hg38.vcf")

    def run(self):
      os.chdir(lovd_method_dir)
      
      # extract_data.py -u http://databases.lovd.nl/shared/ -l BRCA1 BRCA2 -o $LOVD
      lovd_data_host_url = "http://databases.lovd.nl/shared/"
      args = ["extract_data.py", "-u", lovd_data_host_url, "-l", "BRCA1", "BRCA2", "-o", lovd_file_dir]
      print "Running extract_data.py with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)
      print "Extracted data from %s." % (lovd_data_host_url)

      # ./lovd2vcf -i $LOVD/BRCA1.txt -o $LOVD/sharedLOVD_brca1.hg19.vcf -a sharedLOVDAnnotation -b 1 -r $BRCA_RESOURCES/refseq_annotation.hg19.gp -g $BRCA_RESOURCES/hg19.fa
      args = ["./lovd2vcf", "-i", lovd_file_dir + "/BRCA1.txt", "-o", lovd_file_dir + "/sharedLOVD_brca1.hg19.vcf", "-a", "sharedLOVDAnnotation", "-b", "1", "-r", brca_resources_dir + "/refseq_annotation.hg19.gp", "-g", brca_resources_dir + "/hg19.fa"]
      print "Running lovd2vcf with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)
      print "Converted extracted BRCA1 flat file to vcf format."

      # ./lovd2vcf -i $LOVD/BRCA2.txt -o $LOVD/sharedLOVD_brca2.hg19.vcf -a sharedLOVDAnnotation -b 2 -r $BRCA_RESOURCES/refseq_annotation.hg19.gp -g $BRCA_RESOURCES/hg19.fa 
      # Comment: BRCA2.txt might or might not be created. It seems like there's an error condition that kills BRCA2. It's not worth fixing the error condition at this point.
      args = ["./lovd2vcf", "-i", lovd_file_dir + "/BRCA2.txt", "-o", "sharedLOVD_brca2.hg19.vcf", "-a", "sharedLOVDAnnotation", "-b", "2", "-r", brca_resources_dir + "/refseq_annotation.hg19.gp", "-g", brca_resources_dir + "/hg19.fa"]
      print "Running lovd2vcf with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)
      print "Converted extracted BRCA2 flat file to vcf format."

      # vcf-concat $LOVD/sharedLOVD_brca1.hg19.vcf $LOVD/sharedLOVD_brca2.hg19.vcf > $LOVD/sharedLOVD_brca12.hg19.vcf
      shared_lovd_brca12_hg19_vcf_file = lovd_file_dir + "/sharedLOVD_brca12.hg19.vcf"
      writable_shared_lovd_brca12_hg19_vcf_file = open(shared_lovd_brca12_hg19_vcf_file, 'w')
      args = ["vcf-concat", lovd_file_dir + "/sharedLOVD_brca1.hg19.vcf", lovd_file_dir + "/sharedLOVD_brca2.hg19.vcf"]
      print "Running lovd2vcf with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=writable_shared_lovd_brca12_hg19_vcf_file, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)
      print "Concatenated BRCA1 and BRCA2 vcf files into %s." % (shared_lovd_brca12_hg19_vcf_file)
      
      # `CrossMap.py vcf $BRCA_RESOURCES/hg19ToHg38.over.chain.gz $LOVD/sharedLOVD_brca12.hg19.vcf $BRCA_RESOURCES/hg38.fa $LOVD/sharedLOVD_brca12.hg38.vcf
      args = ["CrossMap.py", "vcf", brca_resources_dir + "/hg19ToHg38.over.chain.gz", shared_lovd_brca12_hg19_vcf_file, brca_resources_dir + "/hg38.fa", lovd_file_dir + "/sharedLOVD_brca12.hg38.vcf"]
      print "Running CrossMap.py with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)
      print "Crossmap complete."
      
      # vcf-sort $LOVD/sharedLOVD_brca12.38.vcf > $LOVD/sharedLOVD_brca12.sorted.38.vcf
      with self.output().open("w") as vcf_file:
        args = ["vcf-sort", lovd_file_dir + "/sharedLOVD_brca12.hg38.vcf"]
        print "Running lovd2vcf with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=vcf_file, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)
        print "Sorted BRCA1/2 hg38 vcf file into %s." % (vcf_file)

class DownloadAndExtractFilesFromG1K(luigi.Task):
    date = luigi.DateParameter(default=datetime.date.today())

    def output(self):
      return luigi.LocalTarget(pipeline_input_dir + "/1000G_brca.sorted.hg38.vcf")

    def run(self):
      os.chdir(g1k_file_dir)
      print "Downloading 1000 genome variant data from ftp....takes a while...."

      # wget ftp://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/ALL.chr13.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz
      chr13_vcf_gz_url = "ftp://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/ALL.chr13.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz"
      download_file_and_display_progress(chr13_vcf_gz_url)

      # wget ftp://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/ALL.chr17.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz
      chr17_vcf_gz_url = "ftp://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/ALL.chr17.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz"
      download_file_and_display_progress(chr17_vcf_gz_url)

      # wget ftp://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/ALL.chr13.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz.tbi
      chr13_vcf_gz_tbi_url = "ftp://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/ALL.chr13.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz.tbi"
      download_file_and_display_progress(chr17_vcf_gz_tbi_url)

      # wget ftp://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/ALL.chr17.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz.tbi
      url = "ftp://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/ALL.chr17.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz.tbi"
      download_file_and_display_progress(chr13_vcf_gz_tbi_url)

      print "Extracting BRCA gene region from chr13 and chr17"
      # tabix -h $G1K/ALL.chr13.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz 13:32889080-32973809 > $G1K/chr13_brca2_1000g_GRCh37.vcf
      file_name = g1k_file_dir + "/chr13_brca2_1000g_GRCh37.vcf"
      chr13_brca2_1000g_GRCh37_vcf_file = open(file_name, "w")
      print file_name
      print chr13_brca2_1000g_GRCh37_vcf_file
      args = ["tabix", "-h", g1k_file_dir + "/ALL.chr13.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz", "13:32889080-32973809"]
      print "Running tabix with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=chr13_brca2_1000g_GRCh37_vcf_file, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)

      # tabix -h $G1K/ALL.chr17.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz 17:41191488-41322420 > $G1K/chr17_brca1_1000g_GRCh37.vcf
      file_name = g1k_file_dir + "/chr17_brca1_1000g_GRCh37.vcf"
      chr17_brca1_1000g_GRCh37_vcf_file = open(file_name, "w")
      args = ["tabix", "-h", g1k_file_dir + "/ALL.chr17.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz", "17:41191488-41322420"]
      print "Running tabix with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=chr17_brca1_1000g_GRCh37_vcf_file, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)

      # vcf-concat $G1K/chr13_brca2_1000g_GRCh37.vcf $G1K/chr17_brca1_1000g_GRCh37.vcf  > $G1K/brca12_1000g_GRCh37.vcf
      file_name = g1k_file_dir + "/brca12_1000g_GRCh37.vcf"
      brca12_1000g_GRCh37_vcf_file = open(file_name, "w")
      args = ["vcf-concat", g1k_file_dir + "/chr13_brca2_1000g_GRCh37.vcf", g1k_file_dir + "/chr17_brca1_1000g_GRCh37.vcf"]
      print "Running vcf-concat with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=brca12_1000g_GRCh37_vcf_file, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)

      # CrossMap.py vcf $BRCA_RESOURCES/hg19ToHg38.over.chain.gz  $G1K/brca12_1000g_GRCh37.vcf $BRCA_RESOURCES/hg38.fa  $G1K/1000G_brca.hg38.vcf
      args = ["CrossMap.py", "vcf", brca_resources_dir + "/hg19ToHg38.over.chain.gz", g1k_file_dir + "/brca12_1000g_GRCh37.vcf", brca_resources_dir + "/hg38.fa", g1k_file_dir + "/1000G_brca.hg38.vcf"]
      print "Running CrossMap.py with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)

      # vcf-sort $G1K/1000G_brca.hg38.vcf > $G1K/1000G_brca.sorted.hg38.vcf
      with self.output().open("w") as sorted_1000G_brca_hg38_vcf_file:
        args = ["vcf-sort", g1k_file_dir + "/1000G_brca.hg38.vcf"]
        print "Running vcf-sort with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=sorted_1000G_brca_hg38_vcf_file, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)

        print "Done! Sorted concatenated data into %s" % (sorted_1000G_brca_hg38_vcf_file)

class DownloadAndExtractFilesFromEXAC(luigi.Task):
    date = luigi.DateParameter(default=datetime.date.today())

    def output(self):
      return luigi.LocalTarget(pipeline_input_dir + "/exac.brca12.hg38.vcf")

    def run(self):
      os.chdir(exac_file_dir)

      # Download vcf.gz file
      exac_vcf_gz_url = "ftp://ftp.broadinstitute.org/pub/ExAC_release/current/subsets/ExAC_nonTCGA.r0.3.1.sites.vep.vcf.gz"
      exac_vcf_gz_file_name = exac_vcf_gz_url.split('/')[-1]
      download_file_and_display_progress(exac_vcf_gz_url, exac_vcf_gz_file_name)

      # Download vcf.gz.tbi file
      exac_vcf_gz_tbi_url = "ftp://ftp.broadinstitute.org/pub/ExAC_release/current/subsets/ExAC_nonTCGA.r0.3.1.sites.vep.vcf.gz.tbi"
      exac_vcf_gz_tbi_file_name = exac_vcf_gz_tbi_url.split('/')[-1]
      download_file_and_display_progress(exac_vcf_gz_tbi_url, exac_vcf_gz_tbi_file_name)      

      # tabix -h $EXAC/ExAC_nonTCGA.r0.3.1.sites.vep.vcf.gz 17:41191488-41322420 > $EXAC/exac.brca1.hg19.vcf
      args = ["tabix", "-h", exac_file_dir + "/" + exac_vcf_gz_file_name, "17:41191488-41322420"]
      exac_brca1_hg19_vcf_file = exac_file_dir + "/exac.brca1.hg19.vcf"
      writable_exac_brca1_hg19_vcf_file = open(exac_brca1_hg19_vcf_file, 'w')
      print "Running tabix with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=writable_exac_brca1_hg19_vcf_file, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)
      print "Completed writing %s." % (exac_brca1_hg19_vcf_file)

      # tabix -h $EXAC/ExAC_nonTCGA.r0.3.1.sites.vep.vcf.gz 13:32889080-32973809 > $EXAC/exac.brca2.hg19.vcf
      args = ["tabix", "-h", exac_file_dir + "/" + exac_vcf_gz_file_name, "13:32889080-32973809"]
      exac_brca2_hg19_vcf_file = exac_file_dir + "/exac.brca2.hg19.vcf"
      writable_exac_brca2_hg19_vcf_file = open(exac_brca2_hg19_vcf_file, 'w')
      print "Running tabix with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=writable_exac_brca2_hg19_vcf_file, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)
      print "Completed writing %s." % (exac_brca2_hg19_vcf_file)

      # vcf-concat $EXAC/exac.brca1.hg19.vcf $EXAC/exac.brca2.hg19.vcf > $EXAC/exac.brca12.hg19.vcf
      args = ["vcf-concat", exac_file_dir + "/exac.brca1.hg19.vcf", exac_file_dir + "/exac.brca2.hg19.vcf"]
      exac_brca12_hg19_vcf_file = exac_file_dir + "/exac.brca12.hg19.vcf"
      writable_exac_brca12_hg19_vcf_file = open(exac_brca12_hg19_vcf_file, 'w')
      print "Running tabix with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=writable_exac_brca12_hg19_vcf_file, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)
      print "Completed concatenation of exac brca1/2 data into %s." % (exac_brca12_hg19_vcf_file)

      # CrossMap.py vcf $BRCA_RESOURCES/hg19ToHg38.over.chain.gz $EXAC/exac.brca12.hg19.vcf $BRCA_RESOURCES/hg38.fa $EXAC/exac.brca12.hg38.vcf
      args = ["CrossMap.py", "vcf", brca_resources_dir + "/hg19ToHg38.over.chain.gz", exac_file_dir + "/exac.brca12.hg19.vcf", brca_resources_dir + "/hg38.fa", exac_file_dir + "/exac.brca12.hg38.vcf"]
      print "Running CrossMap.py with the following args: %s" % (args)
      sp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      print_subprocess_output_and_error(sp)
      print "Completed crossmapping hg19 and hg38."

      # vcf-sort $EXAC/exac.brca12.hg38.vcf > $EXAC/exac.brca12.sorted.hg38.vcf
      with self.output().open("w") as vcf_file:
        args = ["vcf-sort", exac_file_dir + "/exac.brca12.hg38.vcf"]
        print "Running tabix with the following args: %s" % (args)
        sp = subprocess.Popen(args, stdout=vcf_file, stderr=subprocess.PIPE)
        print_subprocess_output_and_error(sp)
        print "Completed sorting of exac data into %s." % (vcf_file)

class RunAll(luigi.WrapperTask):
    date = luigi.DateParameter(default=datetime.date.today())
    u = luigi.Parameter()
    p = luigi.Parameter()

    def requires(self):
        yield ConvertLatestClinvarToVCF(self.date)
        yield DownloadAndExtractFilesFromESPTar(self.date)
        yield DownloadAndExtractFilesFromBIC(self.date, self.u, self.p)
        yield DownloadAndExtractFilesFromG1K(self.date)
        yield DownloadAndExtractFilesFromEXAC(self.date)
        yield ExtractAndConvertFilesFromEXLOVD(self.date)
        yield ExtractAndConvertFilesFromLOVD(self.date)