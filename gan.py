import tensorflow as tf
import glob
import imageio
import matplotlib.pyplot as plt
import numpy as np
import os
import PIL
import time

from IPython import display

(X_train, y_train), (X_test, y_test) = tf.keras.datasets.mnist.load_data()

X_train = X_train.reshape(X_train.shape[0], X_train.shape[1], X_train.shape[2], -1).astype('float32')
X_train = (X_train - 127.5) / 127.5

BATCH_SIZE = 256
train_dataset = tf.data.Dataset.from_tensor_slices(X_train).shuffle(60000).batch(BATCH_SIZE)

def make_generator_model():
	model = tf.keras.Sequential()
	model.add(tf.keras.layers.Dense(7 * 7 * 256, use_bias = False,  input_shape = (100, )))
	model.add(tf.keras.layers.BatchNormalization())
	model.add(tf.keras.layers.LeakyReLU())

	model.add(tf.keras.layers.Reshape((7, 7, 256)))
	assert model.output_shape == (None, 7, 7, 256)

	model.add(tf.keras.layers.Conv2DTranspose(128, (5, 5), strides = (1,1), padding = 'same', use_bias = False))
	assert model.output_shape == (None, 7, 7, 128)
	model.add(tf.keras.layers.BatchNormalization())
	model.add(tf.keras.layers.LeakyReLU())

	model.add(tf.keras.layers.Conv2DTranspose(64, (5, 5), strides = (2,2), padding = 'same', use_bias = False))
	assert model.output_shape == (None, 14, 14, 64)
	model.add(tf.keras.layers.BatchNormalization())
	model.add(tf.keras.layers.LeakyReLU())

	model.add(tf.keras.layers.Conv2DTranspose(1, (5, 5), strides = (2, 2), padding = 'same', use_bias = False, activation = 'tanh'))
	assert model.output_shape == (None, 28, 28, 1)

	return model

generator = make_generator_model()
noise = tf.random.normal([1, 100])
generated_image = generator(noise, training = False)

def make_discriminator_model():
	model = tf.keras.Sequential()
	model.add(tf.keras.layers.Conv2D(64, (5, 5), strides = (2, 2), padding = 'same', input_shape = (28, 28, 1)))
	model.add(tf.keras.layers.LeakyReLU())
	model.add(tf.keras.layers.Dropout(0.3))

	model.add(tf.keras.layers.Conv2D(128, (5, 5), strides = (2, 2), padding = 'same'))
	model.add(tf.keras.layers.LeakyReLU())
	model.add(tf.keras.layers.Dropout(0.3))

	model.add(tf.keras.layers.Flatten())
	model.add(tf.keras.layers.Dense(1))

	return model

discriminator = make_discriminator_model()
decision = discriminator(generated_image)

cross_entropy = tf.keras.losses.BinaryCrossentropy(from_logits = True)


def discriminator_loss(real_output, fake_output):
	real_loss = cross_entropy(tf.ones_like(real_output), real_output)
	fake_loss = cross_entropy(tf.zeros_like(fake_output), fake_output)
	total_loss = real_loss + fake_loss
	return total_loss

def generator_loss(fake_output):
	return cross_entropy(tf.ones_like(fake_output), fake_output)

generator_optimizer = tf.keras.optimizers.Adam(1e-4)
discriminator_optimizer = tf.keras.optimizers.Adam(1e-4)

checkpoint_dir = './training_checkpoints'
checkpoint_prefix = os.path.join(checkpoint_dir, "ckpt")
checkpoint = tf.train.Checkpoint(generator_optimizer=generator_optimizer,
	discriminator_optimizer=discriminator_optimizer,
	generator=generator,
	discriminator=discriminator)

EPOCHS = 50
noise_dim = 100
num_examples_to_generate = 16

seed = tf.random.normal([num_examples_to_generate, noise_dim])

@tf.function
def train_step(images):
	noise = tf.random.normal([BATCH_SIZE, noise_dim])

	with tf.GradientTape() as gen_tape, tf.GradientTape() as disc_tape:
		generated_images = generator(noise, training = True)

		real_output = discriminator(images, training = True)
		fake_output = discriminator(generated_images, training = True)

		gen_loss = generator_loss(fake_output)
		disc_loss = discriminator_loss(real_output, fake_output)

	gradients_of_generator = gen_tape.gradient(gen_loss, generator.trainable_variables)
	gradients_of_discriminator = disc_tape.gradient(disc_loss, discriminator.trainable_variables)

	generator_optimizer.apply_gradients(zip(gradients_of_generator, generator.trainable_variables))
	discriminator_optimizer.apply_gradients(zip(gradients_of_discriminator, discriminator.trainable_variables))

def train(dataset, epochs):
	for epoch in range(epochs):
		print(epoch)
		start = time.time()

		for image_batch in dataset:
			train_step(image_batch)

		display.clear_output(wait = True)
		generate_and_save_images(generator, epoch + 1, seed)

		if (epoch + 1) % 15 == 0:
			checkpoint.save(file_prefix = checkpoint_prefix)

		print ('Time for epoch {} is {} sec'.format(epoch + 1, time.time()-start))

	display.clear_output(wait = True)
	generate_and_save_images(generator, epochs, seed)

def generate_and_save_images(model, epoch, test_input):
	predictions = model(test_input, training=False)

	fig = plt.figure(figsize=(4,4))

	for i in range(predictions.shape[0]):
		plt.subplot(4, 4, i + 1)
		plt.imshow(predictions[i, :, :, 0] * 127.5 + 127.5, cmap='gray')
		plt.axis('off')

	plt.savefig('image_at_epoch_{:04d}.png'.format(epoch))
	plt.show()

train(train_dataset, EPOCHS)

anim_file = 'dcgan.gif'
with imageio.get_writer(anim_file, mode = "I") as writer:
	filenames = glob.glob('images*.png')
	filenames = sorted(filenames)
	for filename in filenames:
		image = imageio.imread(filename)
		writer.append_data(image)

import tensorflow_docs.vis.embed as embed
embed.embed_file(anim_file)




















