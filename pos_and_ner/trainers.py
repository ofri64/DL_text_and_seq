from pathlib import Path
from datetime import date
from typing import Tuple
import time

import torch
from torch.utils import data

from pos_and_ner.models import BaseModel
from pos_and_ner.configs import TrainingConfig
from pos_and_ner.predictors import BasePredictor


class ModelTrainer(object):
    def __init__(self, model: BaseModel, train_config: TrainingConfig, predictor: BasePredictor, loss_function):
        self.model = model
        self.train_config = train_config
        self.predictor = predictor
        self.loss_function = loss_function
        self.current_epoch = 0

    def save_checkpoint(self, model_name: str) -> None:
        checkpoint_base_dir = self.train_config["checkpoints_path"]
        current_date = date.today().strftime("%d-%m-%y")

        # construct checkpoint folder name and create it
        checkpoint_path = Path(checkpoint_base_dir) / model_name
        checkpoint_path.mkdir(parents=True, exist_ok=True)
        checkpoint_file = checkpoint_path / f"{current_date}_best_model.pth"

        # save data to disk
        torch.save(self.model.serialize_model(), checkpoint_file)

    def train(self, model_name: str, train_dataset: data.Dataset, dev_dataset: data.Dataset):
        # training hyper parameters and configuration
        batch_size = self.train_config["batch_size"]
        num_workers = self.train_config["num_workers"]
        num_epochs = self.train_config["num_epochs"]
        learning_rate = self.train_config["learning_rate"]
        print_batch_step = self.train_config["print_step"]
        device = torch.device(self.train_config["device"])

        # model, loss and optimizer
        model = self.model
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

        # create data loaders
        train_config_dict = {"batch_size": batch_size, "num_workers": num_workers}
        training_loader = data.DataLoader(train_dataset, **train_config_dict)
        dev_loader = data.DataLoader(dev_dataset, **train_config_dict)

        # Start training
        model = model.to(device)
        start_epoch = self.current_epoch
        best_dev_accuracy = -1000
        for epoch in range(start_epoch, num_epochs):

            model.train(mode=True)
            running_batch_loss = 0
            running_batch_samples = 0
            epoch_train_loss = 0
            epoch_num = epoch + 1

            for batch_idx, sample in enumerate(training_loader, 1):

                x, y = sample
                x, y = x.to(device), y.to(device)

                optimizer.zero_grad()
                outputs = model(x)
                loss = self.loss_function(outputs, y)

                loss.backward()
                optimizer.step()

                # print inter epoch statistics
                epoch_train_loss += loss.item() * len(outputs)
                running_batch_loss += loss.item() * len(outputs)
                running_batch_samples += len(outputs)
                if batch_idx % print_batch_step == 0:
                    print("Train Epoch: {} [{}/{} ({:.0f}%)]\t Average Loss: {:.6f}".format(
                        epoch_num, batch_idx * batch_size, len(train_dataset),
                                   100. * batch_idx / len(training_loader), running_batch_loss / running_batch_samples))
                    running_batch_loss = 0
                    running_batch_samples = 0

            # end of epoch - compute loss on dev set
            epoch_dev_loss = 0
            model.eval()
            total_predictions = 0
            num_correct_predictions = 0
            with torch.no_grad():

                for batch_idx, sample in enumerate(dev_loader):
                    x, y = sample
                    x, y = x.to(device), y.to(device)
                    outputs = model(x)

                    # compute the loss of the batch
                    loss = self.loss_function(outputs, y)
                    epoch_dev_loss += loss.item() * len(x)  # sum of losses, so multiply with batch size

                    # compute number of correct predictions for the batch
                    num_correct_batch, total_predictions_batch = self.predictor.infer_model_outputs_with_gold_labels(outputs, y)
                    num_correct_predictions += num_correct_batch
                    total_predictions += total_predictions_batch

            average_epoch_train_loss = epoch_train_loss / len(train_dataset)
            average_epoch_dev_loss = epoch_dev_loss / len(dev_dataset)
            epoch_dev_accuracy = num_correct_predictions / total_predictions

            print("Epoch {} Loss on Train set is:\t{:.6f}".format(epoch_num, average_epoch_train_loss))
            print("Epoch {} Loss on Dev set is:\t{:.6f}".format(epoch_num, average_epoch_dev_loss))
            print("Epoch {} Accuracy on Dev set is:\t{:.6f}".format(epoch_num, epoch_dev_accuracy))

            # save checkpoint of the model if needed
            if epoch_dev_accuracy > best_dev_accuracy:
                best_dev_accuracy = epoch_dev_accuracy
                print("Epoch {} Saving best model so far with accuracy of {:.6f} on Dev set".format(epoch_num, best_dev_accuracy))
                self.save_checkpoint(model_name)


class AcceptorTrainer(ModelTrainer):

    def __init__(self, model: BaseModel, train_config: TrainingConfig, predictor: BasePredictor, loss_function):
        super().__init__(model, train_config, predictor, loss_function)

    def train(self, model_name: str, train_dataset: data.Dataset, dev_dataset: data.Dataset) -> None:
        # training hyper parameters and configuration
        batch_size = self.train_config["batch_size"]
        num_workers = self.train_config["num_workers"]
        num_epochs = self.train_config["num_epochs"]
        learning_rate = self.train_config["learning_rate"]
        print_batch_step = self.train_config["print_step"]
        device = torch.device(self.train_config["device"])

        # model, loss and optimizer
        model = self.model
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

        # create data loaders
        train_config_dict = {"batch_size": batch_size, "num_workers": num_workers}
        training_loader = data.DataLoader(train_dataset, **train_config_dict)
        dev_loader = data.DataLoader(dev_dataset, **train_config_dict)

        # Start training
        model = model.to(device)
        start_epoch = self.current_epoch
        best_dev_accuracy = -1000
        train_start_time = time.time()
        for epoch in range(start_epoch, num_epochs):

            model.train(mode=True)
            epoch_start_time = time.time()
            running_batch_loss = 0
            running_batch_samples = 0
            epoch_train_loss = 0
            epoch_num = epoch + 1

            for batch_idx, sample in enumerate(training_loader, 1):

                x, y = sample
                x, y = x.to(device), y.to(device)

                optimizer.zero_grad()
                outputs = model(x)
                loss = self.loss_function(outputs, y)

                loss.backward()
                optimizer.step()

                # print inter epoch statistics
                epoch_train_loss += loss.item() * len(outputs)
                running_batch_loss += loss.item() * len(outputs)
                running_batch_samples += len(outputs)
                if batch_idx % print_batch_step == 0:
                    print_time = time.time()
                    print("Train Epoch: {} [{}/{} ({:.0f}%)]\t Average Loss: {:.6f} Training began {} seconds ago".format(
                        epoch_num,
                        batch_idx * batch_size,
                        len(train_dataset),
                        100. * batch_idx / len(training_loader),
                        running_batch_loss / running_batch_samples,
                        int(print_time - train_start_time)))
                    running_batch_loss = 0
                    running_batch_samples = 0

            # end of epoch - compute loss on dev set
            end_of_epoch_time = time.time()
            epoch_dev_loss = 0
            model.eval()
            total_predictions = 0
            num_correct_predictions = 0
            with torch.no_grad():

                for batch_idx, sample in enumerate(dev_loader):
                    x, y = sample
                    x, y = x.to(device), y.to(device)
                    outputs = model(x)

                    # compute the loss of the batch
                    loss = self.loss_function(outputs, y)
                    epoch_dev_loss += loss.item() * len(x)  # sum of losses, so multiply with batch size

                    # compute number of correct predictions for the batch
                    num_correct_batch, total_predictions_batch = self.predictor.infer_model_outputs_with_gold_labels(outputs, y)
                    num_correct_predictions += num_correct_batch
                    total_predictions += total_predictions_batch

            average_epoch_train_loss = epoch_train_loss / len(train_dataset)
            average_epoch_dev_loss = epoch_dev_loss / len(dev_dataset)
            epoch_dev_accuracy = num_correct_predictions / total_predictions

            print("Epoch {} Loss on Train set is:\t{:.6f}".format(epoch_num, average_epoch_train_loss))
            print("Epoch {} Loss on Dev set is:\t{:.6f}".format(epoch_num, average_epoch_dev_loss))
            print("Epoch {} Accuracy on Dev set is:\t{:.6f}".format(epoch_num, epoch_dev_accuracy))
            print("Epoch {} (including prediction) took {} seconds".format(
                epoch_num, int(end_of_epoch_time - epoch_start_time)
            ))

            # save checkpoint of the model if needed
            if epoch_dev_accuracy > best_dev_accuracy:
                best_dev_accuracy = epoch_dev_accuracy
                print("Epoch {} Saving best model so far with accuracy of {:.6f} on Dev set".format(epoch_num, best_dev_accuracy))
                self.save_checkpoint(model_name)


class BiLSTMTrainer(ModelTrainer):

    def __init__(self, model: BaseModel, train_config: TrainingConfig, predictor: BasePredictor, loss_function):
        super().__init__(model, train_config, predictor, loss_function)

    def train(self, model_name: str, train_dataset: data.Dataset, dev_dataset: data.Dataset) -> None:
        # training hyper parameters and configuration
        train_batch_size = self.train_config["batch_size"]
        dev_batch_size = train_batch_size * 40
        num_workers = self.train_config["num_workers"]
        num_epochs = self.train_config["num_epochs"]
        learning_rate = self.train_config["learning_rate"]
        print_batch_step = self.train_config["print_step"]
        device = torch.device(self.train_config["device"])

        # model, loss and optimizer
        model = self.model
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

        # create data loaders
        train_config_dict = {"batch_size": train_batch_size, "num_workers": num_workers}
        dev_config_dict = {"batch_size": dev_batch_size, "num_workers": num_workers}
        training_loader = data.DataLoader(train_dataset, **train_config_dict)
        dev_loader = data.DataLoader(dev_dataset, **dev_config_dict)

        # Start training
        model = model.to(device)
        start_epoch = self.current_epoch
        best_dev_accuracy = -1000
        for epoch in range(start_epoch, num_epochs):

            model.train(mode=True)
            running_batch_loss = 0
            running_batch_samples = 0
            epoch_train_loss = 0
            epoch_num = epoch + 1

            for batch_idx, sample in enumerate(training_loader, 1):

                x, y = sample
                x, y = x.to(device), y.to(device)

                optimizer.zero_grad()
                outputs = model(x)
                loss = self.loss_function(outputs, y)

                loss.backward()
                optimizer.step()

                # print inter epoch statistics
                epoch_train_loss += loss.item() * len(outputs)
                running_batch_loss += loss.item() * len(outputs)
                running_batch_samples += len(outputs)
                if batch_idx % print_batch_step == 0:
                    print("Train Epoch: {} [{}/{} ({:.0f}%)]\t Average Loss: {:.6f}".format(
                        epoch_num,
                        batch_idx * train_batch_size,
                        len(train_dataset),
                        100. * batch_idx / len(training_loader),
                        running_batch_loss / running_batch_samples,
                        ))
                    running_batch_loss = 0
                    running_batch_samples = 0

                    # print accuracy
                    _, dev_accuracy = self.predict_accuracy(model, device, dev_loader)
                    print("After {} sentences, accuracy on dev set is {:.6f}".format(batch_idx * train_batch_size, dev_accuracy))

                    # move model back to training mode
                    model.train(mode=True)

            # end of epoch - compute loss on dev set
            average_epoch_dev_loss, epoch_dev_accuracy = self.predict_accuracy(model, device, dev_loader)
            average_epoch_train_loss = epoch_train_loss / len(train_dataset)
            print("Epoch {} Loss on Train set is:\t{:.6f}".format(epoch_num, average_epoch_train_loss))
            print("Epoch {} Loss on Dev set is:\t{:.6f}".format(epoch_num, average_epoch_dev_loss))
            print("Epoch {} Accuracy on Dev set is:\t{:.6f}".format(epoch_num, epoch_dev_accuracy))

            # save checkpoint of the model if needed
            if epoch_dev_accuracy > best_dev_accuracy:
                best_dev_accuracy = epoch_dev_accuracy
                print("Epoch {} Saving best model so far with accuracy of {:.6f} on Dev set".format(epoch_num, best_dev_accuracy))
                self.save_checkpoint(model_name)

    def predict_accuracy(self, model: torch.nn.Module, device: torch.device, dev_loader: data.DataLoader) -> Tuple[float, float]:
        dev_loss = 0
        model.eval()
        total_predictions = 0
        num_correct_predictions = 0
        with torch.no_grad():

            for batch_idx, sample in enumerate(dev_loader):
                x, y = sample
                x, y = x.to(device), y.to(device)
                outputs = model(x)

                # compute the loss of the batch
                loss = self.loss_function(outputs, y)
                dev_loss += loss.item() * len(x)  # sum of losses, so multiply with batch size

                # compute number of correct predictions for the batch
                num_correct_batch, total_predictions_batch = self.predictor.infer_model_outputs_with_gold_labels(outputs, y)
                num_correct_predictions += num_correct_batch
                total_predictions += total_predictions_batch

        average_dev_loss = dev_loss / total_predictions
        dev_accuracy = num_correct_predictions / total_predictions

        return average_dev_loss, dev_accuracy
