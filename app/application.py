#!/usr/bin/python
import logging

logging.basicConfig(filename='app/logger.log', level=logging.INFO, filemode='w', format='%(asctime)s %(message)s', datefmt='%m/%d - %I:%M:%S')

from flask import Flask, render_template, request, redirect, url_for
from app import app
from .forms import Pipeline
from .forms import Mutate
from .forms import Reads
from library import reads
from library import mutate
from time import sleep
import os
import ConfigParser

Config = ConfigParser.ConfigParser()
Config.read("app/config")


@app.route('/')
def index():
    return redirect(url_for('pipeline'))


@app.route('/stream')
def stream():
    other_root = Config.get('Paths', 'log_root')

    def generate():
        with open(other_root + 'logger.log') as f:
            lines = f.readlines()
            liner = [x.strip() + '\n' for x in lines]
            result = []
            for line in liner:
                if "stream" not in line:
                    result.append(line)
                    if len(result) > 10:
                        result.pop(0)
            return result

    return app.response_class(generate(), mimetype='text/plain')


@app.route('/pipeline', methods=['GET', 'POST'])
def pipeline():
    form = Pipeline()

    if request.method == 'POST':

        if request.form['submit'] == 'Create VCF and Generate Mutations':
            PE100 = Config.get('Profiles', 'PE100')
            indels = Config.get('Profiles', 'indels')
            gcdep = Config.get('Profiles', 'gcdep')
            out_dir_root = Config.get('Paths', 'out_dir_root')
            output = out_dir_root + 'mutations.vcf'
            bed_file_path = form.bed_file.data
            logging.info('New VCF Path: ' + output)

            vcf = form.vcf_path.data
            mutate_rate = int(form.mutation_rate.data)
            chrome_start_input = int(form.chrome_start.data)
            logging.info("Acquired Values")

            mutate.mutating(mutate_rate, vcf, output, bed_file_path, chrome_start_input)

            logging.info("Created VCF")

            fastar = form.fastar.data

            mutate.check_if_dataset_exists(form.data_set.data, fastar)

            mutate.upload_to_db('truth_set_vcf', form.data_set.data, output)

            logging.info("Uploaded to Database")

            ref = reads.get_ref(form.data_set.data)
            fasta = reads.get_fasta_ref(ref)
            base = form.base_error.data
            indel = form.indel_error.data
            newvcf = reads.get_truth_vcf(form.data_set.data)
            newoutput = reads.get_truth_vcf(form.data_set.data)[:-13]

            logging.info('Acquired Values')
            logging.info('Reference FASTA: ' + ref)
            logging.info('Truth VCF: ' + vcf)

            reads.bgzip(vcf)

            logging.info('Zipped VCF')

            reads.simulate(fasta, newvcf + ".gz", base, indel, form.data_set.data, newoutput, PE100, indels, gcdep)

            logging.info('Finished!')

            reads.upload_data(form.data_set.data, out_dir_root)

            logging.info("Uploaded FASTQs to Database")

    return render_template('base.html', title='Pipeline', form=form)


@app.route('/vcf', methods=['GET', 'POST'])
def dbmutate():
    form = Mutate()

    if request.method == 'POST':

        if request.form['submit'] == 'Create Truth VCF':
            vcf = form.vcf_path.data
            out_dir_root = Config.get('Paths', 'out_dir_root')
            output = out_dir_root + 'mutations.vcf'
            #ensure_dir(output)
            mutate_rate = int(form.mutation_rate.data)
            bed_file_path = form.bed_file.data
            chrome_start_input = int(form.chrome_start.data)
            logging.info("Acquired Values")
            logging.info('New VCF Path: ' + output)

            mutate.mutating(mutate_rate, vcf, output, bed_file_path, chrome_start_input)

            logging.info("Created VCF")

            fastar = form.fastar.data

            mutate.check_if_dataset_exists(form.data_set.data, fastar)

            mutate.upload_to_db('truth_set_vcf', form.data_set_mutate.data, output)

            logging.info("Uploaded to Database")

    return render_template('mutations.html', title='Create VCF', form=form)


@app.route('/reads', methods=['GET', 'POST'])
def simreads():
    form = Reads()

    if request.method == 'POST':

        if request.form['submit'] == 'Generate Reads':
            PE100 = Config.get('Profiles', 'PE100')
            indels = Config.get('Profiles', 'indels')
            gcdep = Config.get('Profiles', 'gcdep')
            out_dir_root = Config.get('Paths', 'out_dir_root')
            ref = reads.get_ref(form.data_set_reads.data)
            fasta = reads.get_fasta_ref(ref)
            vcf = reads.get_truth_vcf(form.data_set_reads.data)
            output = reads.get_truth_vcf(form.data_set_reads.data)[:-13]
            base = form.base_error.data
            indel = form.indel_error.data

            logging.info('Acquired Values')
            logging.info('Reference FASTA: ' + ref)
            logging.info('Truth VCF: ' + vcf)

            reads.bgzip(vcf)

            logging.info('Zipped VCF')

            reads.simulate(fasta, vcf + ".gz", base, indel, form.data_set_reads.data, output, PE100, indels, gcdep)

            logging.info('Finished!')

            reads.upload_data(form.data_set_reads.data, out_dir_root)

            logging.info("Uploaded FASTQs to Database")

    return render_template('reads.html', title='Create Reads', form=form)


def ensure_dir(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

